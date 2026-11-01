# Ideate: brainstorming over several rounds

Two models brainstorming together collapse toward the same ideas unless the
rounds are structured. Most of the value comes from independent drafts made
before either side sees the other's; extra rounds after about three add
convergence, not insight.

## Protocol

0. **Write your own list first**, to a file outside the engine's working
   directory (the script runs ideate from an empty temp directory, so anywhere
   else is fine). This is what keeps round 1 independent.
1. **Round 1, `--name <label>`.** The topic, the user's goal, the hard
   constraints, and the output shape: N ideas, each with one line on how it
   differs from the obvious approach. Give it a stance when that widens the
   space ("argue as a Kodi power user", "as the person who maintains this at
   3am"). Do not share your list.
2. **Before reading each answer, write down your current position.** Without
   this you drift toward whatever it said last.
3. **Round 2, `--resume <label>`.** Share your list. Ask it to critique both
   lists, merge them, rank the top K, and name every disagreement. Add: "change
   a position only for a reason you can state; do not concede to converge."
4. **Round 3, `--resume <label> --web live`, the last.** Settle factual disputes with
   evidence: ask it to look each fact up and cite the URL (ideate defaults to the
   cached search index; live search is what settles a disputed fact). End with
   one question: "Does any remaining disagreement change the top K?"

Track rerankings. A model that reorders its top picks after every argument, with
no new evidence, is converging on you, not reasoning; weigh its final order
accordingly.

Judge ideas on their merit; the four verdicts in SKILL.md apply only to the
factual claims an idea rests on. Check those claims, and the URLs behind them.

## Report

- The top K, each with one line of why.
- A disagreement table: your position, its position, how it ended (and on what
  evidence).
- Which facts you verified against a source, and any citation that was wrong
  (in testing a cited comment anchor did not exist, though the claim was right).

## Two engines

Run round 1 on both engines with the identical prompt, in parallel and
independently, then merge the three lists yourself. Continue with whichever
engine's list was strongest.

```bash
bash scripts/pair.sh --engine codex --mode ideate --prompt-file /abs/r1.md --name names
bash scripts/pair.sh --engine codex --mode ideate --prompt-file /abs/r2.md --resume names
```
