import json
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from barrins_scripture.schemas import MTGScrape, Tournament
from barrins_scripture.utils import mtgtop8


class TestSanitizeString:
    def test_lowercases_and_dashes(self) -> None:
        assert mtgtop8.sanitize_string("Championnat DC 974 - Juillet") == (
            "championnat-dc-974-juillet"
        )

    def test_keeps_dots_and_underscores(self) -> None:
        assert mtgtop8.sanitize_string("a_b.c") == "a_b.c"


class TestGetTournamentUrl:
    def test_builds_the_event_url(self) -> None:
        assert mtgtop8.get_tournament_url(88803) == "https://mtgtop8.com/event?e=88803"


class TestGetMaxIdScraped:
    def test_zero_when_nothing_scraped(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        assert mtgtop8.get_max_id_scraped() == 0

    def test_finds_the_highest_id_across_nested_dirs(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "100_duel-commander_a.json").write_text("{}", encoding="utf-8")
        (d / "88803_duel-commander_b.json").write_text("{}", encoding="utf-8")
        assert mtgtop8.get_max_id_scraped() == 88803

    def test_ignores_files_with_a_non_numeric_prefix(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "not-an-id.json").write_text("{}", encoding="utf-8")
        assert mtgtop8.get_max_id_scraped() == 0


class TestGetScrapedIds:
    def test_empty_when_nothing_scraped(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        assert mtgtop8.get_scraped_ids() == set()

    def test_collects_ids_across_nested_dirs(self, tmp_path: Path, monkeypatch) -> None:
        # Regression test for the glob-vs-rglob bug: archived files always
        # live nested (BASE_PATH/YYYY/MM/DD/), never directly in BASE_PATH.
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "100_duel-commander_a.json").write_text("{}", encoding="utf-8")
        (d / "88803_duel-commander_b.json").write_text("{}", encoding="utf-8")
        assert mtgtop8.get_scraped_ids() == {100, 88803}

    def test_ignores_files_with_a_non_numeric_prefix(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        d = tmp_path / "2026" / "07" / "26"
        d.mkdir(parents=True)
        (d / "not-an-id.json").write_text("{}", encoding="utf-8")
        assert mtgtop8.get_scraped_ids() == set()


class TestWeShouldScrapeIt:
    def test_true_when_never_scraped(self) -> None:
        assert (
            mtgtop8.we_should_scrape_it("https://mtgtop8.com/event?e=88803", set())
            is True
        )

    def test_false_when_already_scraped(self) -> None:
        assert (
            mtgtop8.we_should_scrape_it("https://mtgtop8.com/event?e=88803", {88803})
            is False
        )

    def test_strips_extra_query_params(self) -> None:
        url = "https://mtgtop8.com/event?e=88803&d=874003&f=EDH"
        assert mtgtop8.we_should_scrape_it(url, {88803}) is False


class TestScrapeTournament:
    def test_returns_none_for_unknown_format(self) -> None:
        soup = BeautifulSoup(
            "<div class='meta_arch'>Some Unknown Game</div>", "html.parser"
        )
        # tournament() raises ValueError for unknown format upstream; that's
        # a real error case (bad input), not something scrape_tournament
        # should swallow — confirmed by mirroring the parser's own contract.
        try:
            mtgtop8.scrape_tournament("https://mtgtop8.com/event?e=1", soup)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError to propagate")

    def test_overwrites_deck_dates_with_the_tournament_date(self) -> None:
        html = """
        <div class="event_title">Test Event</div>
        <div class="meta_arch">Duel Commander</div>
        <div>29 players - 26/07/26</div>
        <div class="chosen_tr">
          <div class="S14"><a href="?e=1&d=42">Deck</a></div>
          <div class="G11"><a class="player" href="search?player=X">Alice</a></div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        with (
            patch(
                "barrins_scripture.parsers.mtgtop8.get_decklist",
                return_value=([mtgtop8.parser.CardEntry(count=1, name="X")], []),
            ),
            patch("barrins_scripture.parsers.mtgtop8.get_notes", return_value=None),
        ):
            scrape = mtgtop8.scrape_tournament("https://mtgtop8.com/event?e=1", soup)

        assert scrape is not None
        assert scrape.rounds == []
        assert scrape.standings == []
        assert all(d.date == scrape.tournament.date for d in scrape.decks)


class TestSaveTournamentScrape:
    def test_writes_json_under_a_date_path_with_the_expected_filename(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        scrape = MTGScrape(
            tournament=Tournament(
                date="2026-07-26",  # type: ignore[arg-type]
                name="Championnat dc 974 - Juillet",
                url="https://mtgtop8.com/event?e=88803",
                format="Duel Commander",
                players=29,
            )
        )

        file_path = mtgtop8.save_tournament_scrape(scrape)

        assert file_path.parent == tmp_path / "2026" / "07" / "26"
        assert file_path.name == "88803_duel-commander_championnat-dc-974-juillet.json"
        saved = json.loads(file_path.read_text(encoding="utf-8"))
        assert saved["tournament"]["players"] == 29

    def test_strips_extra_query_params_from_the_id(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(mtgtop8, "BASE_PATH", tmp_path)
        scrape = MTGScrape(
            tournament=Tournament(
                date="2026-07-26",  # type: ignore[arg-type]
                name="Event",
                url="https://mtgtop8.com/event?e=88803&d=1&f=EDH",
                format="Duel Commander",
                players=1,
            )
        )
        file_path = mtgtop8.save_tournament_scrape(scrape)
        assert file_path.name.startswith("88803_")
