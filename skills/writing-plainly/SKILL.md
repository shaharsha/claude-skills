---
name: writing-plainly
description: Use when drafting or editing text that someone other than the user will read - Slack, Teams or WhatsApp messages, emails, status and done updates, answers and recommendations, asks, announcements, PR descriptions, tickets, docs - especially drafts sent or posted under the user's name. Also use when the user asks for text that is shorter, simpler, clearer, easier to read, more human or "not AI-generated", says a draft is too long, too formal or reads like a report, or asks how to write a good Slack message or email. Covers English and Hebrew.
---

# Writing plainly

Busy readers skim, decide from the first line whether to keep going, and read length as effort. Text that reads easily and text that doesn't look machine-made come from the same habit: one specific point, first, in plain words, then stop. In a field test a 49-word email got almost twice the replies of a 127-word one, and readers who use AI a lot spot machine text from clusters of habits, not from single words.

## The recipe

Work through these in order. The result is a draft the reader can act on after its first line. The user's own style rules (say, never "we", or no emoji) and the destination's conventions come before these defaults.

1. **Name the one thing.** For yourself, write one sentence: what should the reader know or do after reading?
2. **Open with it.** The first line is the answer, the pick plus a yes or no, the outcome, or the ask. If the reader stops there, they still have it.
3. **Keep only what the reader will use.** Keep a fact if the reader will act on it, would ask for it, or needs it to trust the claim. Leave out what only the writer needed: ticket and PR numbers, commit hashes, file paths, how you checked, the history, options you rejected, and open items nobody asked about. Technical names stay when they are the reader's own words: an engineer choosing a queue needs "SKIP LOCKED", and PR and ticket readers use ids and paths.
4. **Say only what the notes support.** Every fact, number, deadline, default and promise in the draft comes from the user or the material. "We liked library X" stays "liked", not "picked"; retries that help "survive short outages" don't become "never lose events". If the notes contradict each other, ask, don't pick one quietly.
5. **Use the reader's names for things, one name each.** "The dashboard", "the invoices export", not the internal name of a table, script or field, and the same name every time. Name the actual things instead of a category ("the invoices and refunds exports", not "some exports"). Dates the reader can place later ("10 Nov", not "last Tuesday") in anything read after today.
6. **Fit the shape to the genre** (table below). If the destination has a convention, such as a channel's "✅ Done:" posts, read the last few posts and copy the format and length, not the extra items. Bold at most one phrase per message, the thing a skimmer must not miss: a deadline or the ask inside a sentence ("old passwords stop working *Friday*"), or the headline of a long post. None in short messages, never as labels, almost never in email; bold tells readers they may skip the rest.
7. **Write it the way you'd say it to a colleague.** "I" for the sender, contractions, plain verbs (is, has, says, use), active voice. Most sentences under 20 words, some shorter, some longer.
8. **State uncertainty once, concretely**: "estimate from six busy hours", "not tested on PROD yet". One place, not hedging words spread through the text.
9. **Cut, then check.** Cut the draft again, then make sure every question asked and every fact the reader needs is still there. Pipe it through the checker in this skill's folder: `python3 <skill-dir>/scripts/check_text.py - --genre chat < draft.md` (or `email`, `pr`, `ticket`, `doc`). Treat each flag as a prompt to look, fix what makes the draft better, and read it aloud. Rewrite any sentence you wouldn't say that way.

## Shapes by genre

| Genre | Shape |
|---|---|
| Chat reply or DM | 1-4 short lines of plain sentences, answer first. One message with the question in it, not "hi" and then the question. No headings or bold labels; bullets only for 3 or more parallel items. |
| Done or status update | The channel's prefix if it has one, then the outcome. One or two sentences, or a headline plus at most 3 bullets of one fact each. Proof with a number if you have one. Open items only if the reader must act on them. |
| Answer or recommendation | First line: the pick and a yes or no. Then the one or two reasons that decided it, what the reader will notice, the main risk and what handles it, and what is still untested. No tour of every option unless asked. |
| Ask | One request, who must act, and an easy way to answer (yes/no, A or B), ending in a question. A deadline or a fallback ("if I don't hear by Thursday...") only if the user gave one. Mention only the person who must act. |
| Email | Subject: topic plus the ask or date, 3-6 words. Greeting by name, then the answer or ask in the first sentence. Short plain paragraphs, one point each, 50-125 words for a normal ask. Thanks in one line. Non-technical readers: no bullets or bold unless they are real steps. |
| PR description | A verb-first title. One or two lines on what changed and why it matters to users, then the behavior change, how it was tested, and known limits. Short headings are fine; no bold labels on bullets. |
| Ticket or doc | Structure helps here: a verb-first title, why, what, a "Done when" list of things you can observe, out of scope. Sentence-case headings. No traces of the conversation ("I asked X", "as discussed", "X has the numbers"); state the decision and its reason. |

Before drafting a Slack or Teams message, read [references/slack-and-chat.md](references/slack-and-chat.md) (formatting that renders, threads, mentions, announcements). Before drafting an email, read [references/email.md](references/email.md) (subject lines, replies in a thread, follow-ups, bad news).

## Example

A teammate asks: "is the export ready for the client demo tomorrow?" The notes say 9 of 10 report types export fine, the invoices export times out above about 50k rows, filtering by month works around it, the fix (N+1 queries in the export function, ticket EXP-881) lands Tuesday, and it was checked on staging with the client's data.

Without the recipe:

> Great question! Here's a quick status update on the export feature:
> **What's working:** 9 out of 10 report types export cleanly on staging.
> **Known issue:** The invoices export times out on large datasets (50k+ rows) due to N+1 queries (EXP-881).
> **Recommendation:** Filter invoices by month for the demo.
> Let me know if you have any questions!

With it:

> Yes, except one report. Invoices time out above about 50k rows, so for the demo filter them by month and they export fine. The real fix lands Tuesday.

## Tells that make text read as machine-written

Use this list in the edit pass. Swapping words alone doesn't fix it: in a 2025 study, readers who use AI a lot still caught "humanized" text from what was left over. Specific content is what fixes it.

| Tell | Write instead |
|---|---|
| Clusters of delve, crucial, pivotal, underscore, showcase, testament, vibrant, foster, enhance, robust, seamless, leverage, landscape, multifaceted | The plain word, or the fact the word stood in for |
| Inflated importance: "plays a key role", "marks a shift", a trailing ", highlighting its importance" | The fact; let the reader judge how much it matters |
| Stock shapes: "not just X, but Y", "it's not X, it's Y", "X rather than Y", lists of exactly three | The positive claim alone; as many items as there really are |
| "serves as", "boasts", "features" | "is", "has" |
| Bold lead-in labels ("**Retries.**", "Why it wins:"), headings inside a message | Plain sentences; real headings only in PRs, tickets and docs |
| "Great question", "I hope this finds you well", "Let me know if you have any questions", a closing summary | Start with the point; stop when it's made |
| Em dashes | A period, comma, colon or parentheses, usually by restructuring the sentence |
| "Experts say", "studies show" | Name the source, or drop the claim |
| "May potentially", "it's important to note" | One concrete statement of what's uncertain |
| Sentences of the same length, bullets of the same shape | Vary them; merge or cut bullets that repeat a pattern |

The full list, including which words newer models favor, is in [references/ai-tells.md](references/ai-tells.md).

## Hebrew

- Start every sentence and every line with a Hebrew word. A line that starts with a number, an English word or an id renders left-to-right in Slack, WhatsApp and Gmail and scrambles its punctuation. Move the number inside: "החדרים 204 ו-311 ..." rather than "204 ו-311 ...".
- Plain hyphen only, ranges included (5-15). No en or em dashes. For "leads to" use ←, since → points backwards in right-to-left text.
- Answer in the thread's language. Keep product and button names as they appear on screen.
- In chat, write the way people type: short and direct. Formal connectors (בנוסף, יתרה מזאת, חשוב לציין, לסיכום) read as machine- or lawyer-written.
- Email: "היי" or "שלום" plus the name, and "תודה", with people you work with; "שלום רב" and "בברכה" for first contact with officials or senior people.

## Common mistakes

| Mistake | Fix |
|---|---|
| A short message shaped like a report: title, headings, "Found / Did / Open" labels | Plain sentences, or the channel's own format |
| A category where the reader needs names: "some sources weren't scheduled" | Name them |
| Every true fact you have | Only what the reader acts on; the rest is there if they ask |
| A recommendation that walks through every option | The pick, why, the one risk |
| Prose when the channel posts "✅ Done:" lines | Copy the channel's format |
| An FYI about something still being decided, written as if it were settled | Say it is not decided yet, or wait and send it once it is |
| A new message about something that already has a thread | Reply in the thread |
| Replacing every em dash with a comma and calling it done | Restructure the sentence; fix the content, not just the punctuation |

Why these rules, with the studies and numbers behind them: [references/evidence.md](references/evidence.md).
