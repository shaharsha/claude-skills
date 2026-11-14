# writing-plainly

Write messages, emails, updates, PR descriptions and tickets that people read to the end and that don't read as AI-generated. One recipe for every genre, the evidence behind it, Slack and email specifics, a Hebrew section, and a small checker that flags the mechanical tells.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Ask a model for "a short Slack update" and you get a correct, polite, slightly too long text with a bold label on every line, the ticket numbers from your notes, an open item nobody asked about, and a closing line that sums it all up. Each piece is defensible; together they read like a report written by a machine, and busy readers skim past them.

Two bodies of evidence point the same way:

- **Shorter gets read and answered.** In Rogers and Lasky-Fink's field experiments, a 49-word email got almost twice the responses of a 127-word one, and readers judged the work a reply would take from the length alone. Nielsen Norman Group measured 58% better usability from halving the words.
- **Machine text is spotted from clusters, not single words.** People who use ChatGPT a lot labelled 299 of 300 articles correctly, mostly from vocabulary and sentence templates, and still caught text rewritten to dodge their own list of cues. Swapping words doesn't fix it; specific content does.

The skill also encodes what one heavy user actually pushed back on across many real drafts: report-shaped short messages, categories instead of names, internal ids, open items nobody asked about, and option tours when he asked for a recommendation.

## What it does

```
notes ──▶ name the one thing ──▶ open with it ──▶ keep what the reader uses
                                                  say only what the notes support
                                                  the reader's names, one each
      ──▶ shape for the genre (chat · done update · answer · ask · email · PR · ticket)
      ──▶ write it like you'd say it ──▶ cut, check, read aloud
```

- [SKILL.md](SKILL.md): the recipe, a shape per genre, a before/after example, the AI tells with what to write instead, Hebrew rules, common mistakes.
- [references/slack-and-chat.md](references/slack-and-chat.md): status updates, asks, FYIs, threads, announcements, formatting that actually renders.
- [references/email.md](references/email.md): subject lines, openings, length, asks and follow-ups, thanks, bad news, with the evidence graded.
- [references/ai-tells.md](references/ai-tells.md): the fuller list of tells, which words newer models favor, and what doesn't work as a sign.
- [references/evidence.md](references/evidence.md): the studies and numbers behind each rule.
- `scripts/check_text.py`: flags em dashes, AI-associated words, stock contrasts, bold lead-in labels, headings in messages, long sentences, and Hebrew lines that would render left-to-right.

## Tested

Eight realistic tasks (a Slack done update, an email to a non-technical partner, a PR description, a recommendation DM, a Hebrew WhatsApp reply, a Linear ticket, a bad-news email to a client, a Slack review request), each written by the same model with and without the skill, then reviewed by Codex and Gemini. With the skill, drafts were 30-45% shorter on the longer genres, dropped internal ids and bold labels, kept the mechanism engineers need, and invented nothing the notes didn't say. Two of the eight tasks were held out of tuning.

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install writing-plainly@shaharsha-skills
```

That installs only this skill. For the whole `documents-and-decks` bundle, run `/plugin install documents-and-decks@shaharsha-skills` instead.

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/writing-plainly" ~/.claude/skills/writing-plainly
```

## Requirements

None for the skill itself. The checker needs Python 3 (standard library only).

## Quick start

Ask for any draft as usual ("draft a Slack update for #engineering about the fix", "reply to Dana's email", "write the PR description"). The skill triggers on drafting text for other people, and on requests like "shorter", "simpler" or "doesn't sound like AI".

Check a draft yourself:

```bash
python3 ~/.claude/skills/writing-plainly/scripts/check_text.py - --genre chat < draft.md
python3 ~/.claude/skills/writing-plainly/scripts/check_text.py email.txt --genre email --max-words 125
```

## Gotchas

- **Your own rules win.** If you never want "we", or want emoji, say so (in a CLAUDE.md or memory); the skill's defaults give way to the user's rules and the channel's conventions.
- **The checker is advisory.** A flag is a prompt to look again. One "crucial" is fine; a cluster is the tell.
- **Cutting can go too far.** The recipe keeps technical names when they are the reader's own words, and never adds deadlines, defaults or promises the notes didn't give.
- **Hebrew in chat apps** renders a line left-to-right when it starts with a number or a Latin word. Start each sentence with a Hebrew word.

## Related skills

- [tech-design-doc](../tech-design-doc): long-form design docs, RFCs and ADRs.
- [writing-project-instructions](../writing-project-instructions): CLAUDE.md and AGENTS.md files.
- [pair-intelligence](../pair-intelligence): a second model's review of a draft before it goes out.

## License

MIT.
