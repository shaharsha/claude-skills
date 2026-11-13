# Consult: a second opinion on a decision or diagnosis

Use it to choose between options, to explain a failure you cannot settle, or to
check a claim before you build on it. It is lighter than a review: one question,
one answer, read-only, usually 15 seconds to 2 minutes at the default effort.

## The prompt

```
<question>
One sentence: what to decide or explain.
</question>

<context>
Facts the other model cannot find on its own: what the code is for, who runs it,
whether inputs are trusted, what is already settled and why, what you measured.
Name the files to read, with paths. It reads beyond what you name only sometimes,
and its best catches come from the files you point it at.
</context>

<options>
A. ...   B. ...   C. ...
Neutral descriptions in no particular order. You may propose an option not listed.
</options>

<answer_format>
1. Your pick or diagnosis, in one sentence.
2. The reasons, each tied to a file and line, a measurement, or a source, and
   marked "read" (you saw it at that file:line or URL) or "inferred".
3. The strongest case against your pick, and what would change your mind.
4. What you could not verify by reading.
Plain prose, citations as plain path:line (no links): about 15 lines for two or
three options, a few more for each option beyond that.
</answer_format>
```

The read/inferred mark is what makes an answer quick to check: four sessions
(2026-11-11 to 13) said the answers they could adjudicate fastest quoted a file
and line for every fact, and the claims that failed were the unmarked runtime
inferences. Gemini otherwise wraps citations in `file://` links, slow to read.

**When the question is a list of claims to check** (your draft's facts, another
session's summary), number them and ask for one line each:
`C3: CONFIRMED | REFUTED | PARTLY - path:line - what the source says`.

**Before one live command** (a PROD write, a migration, a key rotation), ask in
this shape, which three sessions wrote by hand:

```
<command>
The exact command, verbatim, and where it runs.
</command>
<before>
What must be true first, and how each is checked.
</before>
<after>
The checks after it ran, and what each result means.
</after>
<way_back>
The rollback, verbatim, and what it cannot undo.
</way_back>
Is the command right as written? Report what to change in any of the four parts,
each tied to a file and line or a doc.
```

Leave out your own lean, which option you prefer, and how confident you are. A
model given your conclusion grades the conclusion instead of the problem. You
may say where you are least sure ("the retry path is what I most want checked"),
which directs attention without supplying an answer.

**When you ask for a critique of a design you already have**, ask first for the
model's own design for the same goal and constraints, then for its critique of
yours, in that order and in one prompt: "First sketch how you would do it. Then
compare ours with your sketch: where yours is better, where ours is, and what
neither handles." A model that reads your design first tends to patch it; with
its own sketch on the page it names the gaps its design has and yours lacks
(2026-11-07: an invite-flow consult to both engines this way gave two different
concrete gap lists, product detail from Gemini, identity lifecycle from Codex).

Tell the model what it may do, in these words: "You may read any file and run
read-only commands (cat, rg, git log); you cannot write files or run tests."
Codex reads files only through shell commands, so a prompt saying it "cannot run
anything" gets an answer from the prompt alone: three rounds did on 2026-11-02 to
11-04, and pair.sh now stops such a round with `STATUS=unread`. A claim about
runtime behaviour is still inference (in read-only mode even `python3` fails in
Codex's macOS sandbox); when the decision turns on one, run it yourself: call the
function on sample inputs, run the test.

Point `--cwd` at the narrowest directory that holds what the question needs. To
show it other repositories, or a ref other than the checked-out one, stage them:
`bash scripts/pair_stage.sh /tmp/<name> <repo>[@<ref>][:<paths>] ...` writes a
snapshot of each with a `SHAS.md` of the commits; cite that file in the prompt.
List a repository twice for two refs; add `--exclude '*.mp4'` (before the folder)
to leave out recordings and other bulk; stage loose files (a settings file, a
script outside any repo) as `file:<path>`, which `SHAS.md` maps back to the
original path, and a revised plan as `delta:<old>,<new>`, the plan beside its diff
from the revision the last round read (`references/prompts.md`, *A revised plan*). A copy staged by hand can shadow the real path the code reads, and
the model then reasons about the copy (2026-11-06: one refuted claim came from
exactly that). When
the repository is a grab-bag of unrelated private files, or the file in question
embeds a secret, copy the relevant files (redacted) into a temp directory and
point `--cwd` there. Without `--cwd`, consult runs in the current directory.

A spec is a path, relative to where you run the script, not a repository name:

```bash
bash scripts/pair_stage.sh /tmp/stage-x ~/Projects/api@origin/main:src,tests \
  ~/Projects/infra@origin/main:modules/dns "file:$HOME/.claude/plans/x.md"
bash scripts/pair_stage.sh /tmp/stage-skill "file:$HOME/.claude/skills/foo" "file:/tmp/foo-evals/outputs"
```

`--out-dir <dir>` copies the answer (and its meta.json) next to the rest of your
evidence and prints `COPY=`; the run folder stays under `~/.cache/pair-intelligence`.

## Non-code documents

A contract, a policy, a pitch or a research write-up is consulted the same way,
and it worked well in practice (11 of 11 findings held up on a legal review):

- Extract every binary first (`pandoc --track-changes=all` for .docx,
  `pdftotext` for PDFs) and say in the prompt how reliable each extraction is.
  Facts that live only in email or chat go in a short facts file that states its
  own source.
- Restate your analysis as numbered, checkable claims (1.1, 1.2, R3...), so every
  finding can cite a claim and a source line.
- Give it a role that fits the document ("a story editor", "opposing counsel")
  and the brief in the user's own words: without the brief, a critique drifts
  toward its own taste (a comedy pitch was pushed toward drama).
- Stage the files in a scratch directory and point `--cwd` at it, so the other
  model cannot wander into unrelated private files. Ask the user before sending
  personal or legal material to another vendor.
- **Reviewing writing** (drafts, a skill's prose, a message): an editor role, the
  brief in the user's own words, then per draft a verdict with the exact
  replacement text, then any conflict between instructions. A style opinion
  ("reads as machine rhythm") is a claim like any other: check it against the
  brief, which may ask for exactly that. When the review tests a skill, stage the
  outputs with and without it, so the reviewer can tell what the skill caused.

## After the answer

- Adjudicate each reason as in SKILL.md. Check the extent: an answer that names
  three failing inputs often has a fourth class it did not see.
- Check the facts a pick rests on, not only its reasoning: the main reason for a
  pick can be a confident factual error. Measured on 2026-11-02: Gemini argued
  against switching to a library because it "risks invalidating already-registered
  keys", and the library's own documentation shows key import
  (`import_keys()`). A sound argument from a false premise still picks wrong.
- If you dispute a specific claim, resume the same session once with the evidence
  ("`pay.py:42` takes the lock before the read at line 47") and ask it to re-derive
  the claim against the source, not whether it agrees with you.
- For a contested call, ask both engines with the identical prompt, in parallel,
  with their logs written outside `--cwd` (each could otherwise read the other's
  answer). Compare picks: where they differ, read the source before deciding.

## Example run

```bash
bash scripts/pair.sh --engine codex --mode consult \
  --cwd /abs/repo --prompt-file /abs/consult.md --name fx-filter
bash scripts/pair.sh --engine codex --mode consult \
  --prompt-file /abs/followup.md --resume fx-filter
```
