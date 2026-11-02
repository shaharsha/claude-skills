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
2. The reasons, each tied to a file and line, a measurement, or a source.
3. The strongest case against your pick, and what would change your mind.
4. What you could not verify by reading.
Plain prose, at most 15 lines.
</answer_format>
```

Leave out your own lean, which option you prefer, and how confident you are. A
model given your conclusion grades the conclusion instead of the problem. You
may say where you are least sure ("the retry path is what I most want checked"),
which directs attention without supplying an answer.

The model cannot run anything in read-only mode (even `python3` fails in Codex's
macOS sandbox), so say so in the prompt and treat every claim about runtime
behaviour as inference. When the decision turns on one, run it yourself: call the
function on sample inputs, run the test.

Point `--cwd` at the narrowest directory that holds what the question needs. When
the repository is a grab-bag of unrelated private files, or the file in question
embeds a secret, copy the relevant files (redacted) into a temp directory and
point `--cwd` there. Without `--cwd`, consult runs in the current directory.

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
- For a contested call, ask both engines with the identical prompt, in parallel.
  Compare picks: where they differ, read the source before deciding.

## Example run

```bash
bash scripts/pair.sh --engine codex --mode consult \
  --cwd /abs/repo --prompt-file /abs/consult.md --name fx-filter
bash scripts/pair.sh --engine codex --mode consult \
  --prompt-file /abs/followup.md --resume fx-filter
```
