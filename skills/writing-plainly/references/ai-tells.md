# Signs of machine-written text

The fuller version of the tells table in SKILL.md, for the edit pass and for reviewing someone else's draft. Mostly from Wikipedia's "Signs of AI writing" field guide (maintained by WikiProject AI Cleanup, updated through late 2026) and Russell et al. (ACL 2025).

Two things to hold on to:

- **One sign proves nothing.** People wrote "crucial" long before chatbots. What gives text away is a cluster, and Wikipedia's editors call a high density of these words "one of the strongest tells".
- **Fixing the surface isn't enough.** When researchers had a model rewrite its text to avoid every cue the experts had listed, the experts' majority vote still caught all of it, from what was left: formal titles, stiff quotes, safe phrasing. Text reads as human when it has specific content: names, numbers, a reason for writing, an opinion.

## How experts spotted it

Russell et al. asked people who use ChatGPT a lot to label 300 articles. A majority vote of five of them got 299 right, better than most commercial detectors. Their explanations cited:

| Cue | Share of explanations |
|---|---|
| Vocabulary | 53% |
| Sentence structure (templates, lists of three, same lengths) | 36% |
| Grammar and punctuation (too clean) | 25% |
| Originality (safe, no surprise or wit) | 24% |
| Quotes (stiff, every source sounds alike) | 22% |
| Clarity (over-explains, explains instead of showing) | 20% |

People who rarely use chatbots did little better than chance and were overconfident.

## Vocabulary

Words that are fine alone and tell-tale in clusters. The favorites change by model generation:

- **2023 to mid-2024:** additionally, boasts, bolstered, crucial, delve, emphasizing, enduring, garner, intricate, interplay, key, landscape, meticulously, pivotal, underscore, tapestry, testament, valuable, vibrant
- **Mid-2024 to mid-2025:** align with, bolstered, crucial, emphasizing, enhance, enduring, fostering, highlighting, pivotal, showcasing, underscore, vibrant
- **Mid-2025 to mid-2026:** emphasizing, enhance, highlighting, showcasing
- **Mid-2026 on:** challenge, clearer, dependable, echoed, foster, leverage, matters, multifaceted, practical, prioritize, quietly, steady, universally, with more periods and short sentences

Banning words just moves a model to the next favorite. Describe what you want instead, and give examples of the writer's own text.

## Content

- **Inflated significance**: "stands as", "is a testament to", "plays a pivotal role", "marks a shift", "evolving landscape", "setting the stage for", tying a small fact to a big theme.
- **Trailing "-ing" analysis**: "..., highlighting its importance", "..., reflecting broader trends", "..., ensuring ...".
- **Vague association**: "associated with", "in connection with" where a direct fact belongs ("was CEO of", "taught at").
- **Vague sources**: "experts argue", "observers have noted", "several sources" when there are two.
- **Formula endings**: "Despite these challenges...", a future-outlook paragraph, a summary that repeats everything.
- **Coverage instead of content**: "has been featured in national media" without saying what was said.

## Sentence shapes

- **Contrasts**: "not just X, but also Y", "it's not X, it's Y", "no X, no Y, just Z", and the newer "Y rather than X".
- **Lists of three**: "clear, concise, and compelling". Use as many items as there are.
- **Avoiding is/has**: "serves as", "functions as", "boasts", "features", "offers".
- **Same rhythm**: every sentence 15-20 words, every paragraph the same shape, every bullet "Label: fragment".

## Formatting

- Title Case Headings; bold on every other phrase; emoji at the start of headings or bullets; bullets that open with a bold label; Markdown in places that don't render it.
- Em dashes used heavily. Wikipedia lists heavy em-dash use as a historical sign (2022 to September 2026). Newer models moved to periods and short sentences, but many readers still treat the em dash as a tell.
- Curly quotes in places where people type straight ones.

## Leftover chat

- "Certainly!", "Great question", "I hope this helps", "Let me know if you'd like...", "Here is a...".
- Hedges about sources: "based on available information", "not widely documented", "should be treated as ... rather than ...".
- Placeholders: "[Your Name]", "2026-XX-XX", "INSERT_LINK".

## What reads as human

- Plain verbs: "is", "has", "says", "used", "tried", "died", not "serves as", "utilized", "attempted", "passed away".
- Definite claims when the facts support them: "the only", "the first", "one of the best". Not as a style device.
- Honest qualifiers used once: "probably", "tends to".
- Specific details: names, amounts, dates, a concrete reason for writing.
- Uneven sentence lengths, a short fragment now and then, and occasional brackets and contractions.

## Not reliable signs

Perfect grammar, formal or academic prose, a mix of casual and formal registers, "bland" text, transition words on their own, and unsourced claims all show up in plenty of human writing. Detector scores have meaningful error rates and are easy to fool with paraphrasing.

## Hebrew

There is little published research on Hebrew AI tells. What reads machine-made in practice: formal connectors in casual settings (בנוסף, יתרה מזאת, חשוב לציין, לסיכום, מעבר לכך), "באופן משמעותי" and similar adverbs, the same contrast and list-of-three shapes, and translated-English phrasing. Lines that start with a Latin word or a number also break the right-to-left layout, which no Hebrew speaker would leave in.

## Sources

- Wikipedia, Signs of AI writing: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Russell et al., "People who frequently use ChatGPT for writing tasks are accurate and robust detectors of AI-generated text", ACL 2025: https://arxiv.org/abs/2501.15654
- Kobak et al., excess vocabulary in PubMed abstracts, Science Advances 2025 (the "delve" study)
