"""Run all CI checks locally (mirrors .github/workflows/CI.yml's scripture job).

Usage:
    python scripts/workflow_ci.py               # fix + unit tests
    python scripts/workflow_ci.py --no-fix      # check only, no auto-fix
    python scripts/workflow_ci.py --integration # include @pytest.mark.integration tests
    python scripts/workflow_ci.py --no-tests    # skip pytest
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()


def run(name: str, cmd: list[str], failures: list[str]) -> None:
    print(f"\n==> {name}", flush=True)
    result = subprocess.run(cmd, cwd=REPO_ROOT)  # noqa: S603
    if result.returncode != 0:
        print(f"    FAILED (exit {result.returncode})")
        failures.append(name)
    else:
        print("    OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local CI runner.")
    parser.add_argument("--no-fix", action="store_true", help="Check only, no auto-fix")
    parser.add_argument("--no-tests", action="store_true", help="Skip pytest")
    parser.add_argument(
        "--integration", action="store_true", help="Include integration tests"
    )
    args = parser.parse_args()

    failures: list[str] = []

    # --- lint & format ---
    if args.no_fix:
        run("ruff check", ["ruff", "check", "."], failures)
        run(
            "ruff format (check)",
            ["ruff", "format", "barrins_scripture", "tests", "--check"],
            failures,
        )
    else:
        run("ruff check (fix)", ["ruff", "check", ".", "--fix"], failures)
        run("ruff format", ["ruff", "format", "barrins_scripture", "tests"], failures)

    # --- security ---
    run("bandit", ["bandit", "-r", "barrins_scripture/", "-ll"], failures)

    # --- type check ---
    run("ty", ["ty", "check", "barrins_scripture/"], failures)

    # --- tests ---
    if not args.no_tests:
        pytest_cmd = ["pytest", "tests/"]
        if not args.integration:
            pytest_cmd += ["-m", "not integration"]
        run("pytest", pytest_cmd, failures)

    # --- summary ---
    print()
    if not failures:
        print("All checks passed.")
        sys.exit(0)
    else:
        print(f"Failed steps: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
