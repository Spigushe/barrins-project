---
name: natural-writing
description: Write or rewrite a text (English or French) to strip out the stylistic tells that give away an AI origin — the "GPT-isms" vocabulary, the formulaic em dash, bold-lead-in bullet lists, repetitive logical connectors, a smoothed-over tone with no rough edges. Use this by default whenever the user asks to write, rewrite, "make it sound more natural/human," "make it less AI," or produce text meant to be read as written by a person (a resume, a cover letter, a LinkedIn post, an email, an article, a letter to a lawyer or HR) — even if they never say "AI detection" outright.
---

# Natural writing (anti-AI-marker pass)

This skill exists to produce text without the stylistic tics statistically associated with LLM output. The goal isn't fooling a detector — it's recovering prose that reads like someone who writes fast and lets a few rough edges show. That's also, simply, better writing.

One caveat worth keeping in mind: no single tell proves anything on its own. It's the pile-up that gives a text away. The list below shifts with every model generation — treat it as a starting point to revise, not a fixed law.

## Process

1. **Write the substance first, normally.** Don't trade clarity or accuracy for "sounding human" — a confusing text helps no one.
2. **Run the draft through the filters below**, one at a time.
3. **Read it back as if speaking it aloud.** A sentence nobody would actually say out loud is suspect.
4. For a long piece, work section by section rather than trying to fix the whole thing in one pass.

## Filter 1 — vocabulary to cut or ration heavily

### English (the most documented, and it shifts by model generation)
`delve, leverage, navigate (figurative), elevate, intricate/intricacies, meticulous(ly), synergy, empower, landscape (figurative), ecosystem (figurative), underscore, seamless, robust, game-changer, boasts, bolstered, crucial, garner, interplay, pivotal, tapestry, testament, vibrant, fostering, showcasing, align with, enhance, nestled in the heart of, a diverse array of, renowned, groundbreaking, committed to`

### Common French equivalents to watch for
`il est essentiel/crucial de, au cœur de, un véritable enjeu, façonner, un écosystème, une synergie, un tournant majeur, riche/foisonnant, souligner l'importance de, il convient de noter que, dans un monde en constante évolution, un panel diversifié, incontournable, de plus en plus, revêt une importance`

**Rule of thumb**: if a word from this list shows up, swap it for something plain and concrete, or rework the whole sentence — not just the word, since the surrounding structure can still read as machine-written even after a synonym swap.

## Filter 2 — punctuation

- **The em dash (—)**: LLMs overuse it, often padded with spaces on both sides, standing in for a comma, parentheses, or a colon. Swap it for a comma, a period, parentheses, or split the sentence in two. An occasional dash is normal; it's the frequency and the pattern ("X — Y — often for emphasis") that gives it away.
- Systematic curly quotes, "clean" ellipses (…), en dashes in number ranges — prefer the punctuation a person actually types quickly (straight quotes, "...", a plain hyphen).
- Don't overuse a colon to introduce a list inside a sentence that's otherwise conversational.

## Filter 3 — structure

- **No bold-lead-in bullet lists** ("**Term**: explanation") unless the user explicitly asked for one or the format genuinely calls for it (a spec sheet, say). Default to continuous prose.
- Avoid paragraphs that are strictly symmetrical — same length, same repeated subject-verb-object shape.
- Avoid systematic contrastive constructions ("While X..., Y...").
- Vary sentence length. Mix short and long, don't settle into one steady rhythm.

## Filter 4 — logical connectors opening a sentence

Cut or heavily ration, paragraph after paragraph: `Moreover, Furthermore, Additionally, Importantly` (or their French equivalents: `De plus, Par ailleurs, En outre, Il est important de noter que`). One connector now and then reads naturally; using one to open every paragraph mechanically doesn't. Prefer an implicit link — the next idea should follow on its own — or pick the previous subject back up instead.

## Filter 5 — tone and voice

- Reach for **concrete, specific detail** over generalities — a proper name, an exact date, a real number, a small anecdote. Recent research flags this as one of the strongest "human" signals.
- Allow **controlled irregularity**: a sentence that digresses slightly, a personal aside, a flash of humor or irritation where the context allows it.
- Avoid a flat, neutral-polite-corporate register that never shifts. If the context is an email to a friend, an HR letter, a post about basketball, actually adjust the register — not just swap two words and call it done.
- Avoid closing a paragraph with a hollow generality like "This shows the importance of X" that adds nothing new.

## Filter 6 — final self-check

Before handing the text over, run through this list and fix anything that trips it:
- Is there an em dash padded with spaces on both sides? Fix it.
- Is there a word from Filter 1? Fix it.
- Is there an unrequested bold-lead-in bullet list? Convert it back to prose.
- Does every paragraph open with an explicit logical connector? Break the pattern.
- Does the text carry at least one concrete, specific detail (a name, a number, a date) rather than only generalities? If not, add one where the context genuinely supports it and it's true.

**Important**: this filter must never lead to inventing facts, quotes, or details to make a text "feel real." Accuracy of the content stays the priority (see the user's stated preferences) — style is a matter of form, never of substance.
