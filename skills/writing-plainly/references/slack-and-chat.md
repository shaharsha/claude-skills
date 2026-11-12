# Slack and other work chat

Rules specific to Slack, Teams and similar chat, on top of the recipe in SKILL.md. Sources at the end; where a rule rests on advice rather than data, it says so.

## Status and done updates

- First line: the state and the result ("Migration done, PROD healthy since 14:10"). Readers scan updates for "blocked" and for their own name.
- Several items: short bullets, one fact each. A status emoji per item (✅ done, 🟡 in progress, 🔴 blocked) helps triage when there are several; skip it for a single item. (One Slack blog example, not measured.)
- Incident updates: current status, who is affected, what you know, and when the next update comes. That stops the "any news?" pings.
- Detail goes in a thread under the update or in a linked doc or ticket. Chat is not the record; some workspaces keep only 90 days.

## Asks

- One self-contained message: greeting, context and the question together. A lone "hi" makes the other person wait for the real message (nohello.net; Slack and GitLab say the same).
- One request. Name who must act and @mention only them; say why them ("you built the importer").
- Offer closed options (A or B, yes or no). If the user set a deadline or a default, state it with a time zone so silence still resolves it ("If no objection by 5pm CET, I'll ship it"). Don't invent either.
- No reply? Follow up once with something new: a narrower question or a proposed default. Not "any thoughts? 👀".

## FYIs

- Open with the fact, then say whether anything is needed ("No action needed").
- Post in the topical channel, not a DM. Spell names without @ when you only want them to know.
- One topic per message; every message is a notification.
- Say whether it is decided. An FYI that reads as settled while it is still open invites a debate nobody asked for; either mark it as open or send it once it is decided.

## Thread replies

- Continue in the thread; don't start a new top-level message about something a thread already covers. A new subject gets a new message.
- Tick "Also send to channel" only for a decision or a deadline change everyone needs.
- Pure acknowledgement is a reaction (👀 looking, ✅ done, 👍 agree), not "OK" or "will do".
- When a question is resolved, post the answer in the thread so the next person finds it.

## Announcements

- A one-line headline, then the key fact, the date it takes effect, and what people must do.
- @channel and @here only for urgent, time-bound changes. @channel notifies everyone, including people who are away; @here only those active. Neither notifies inside threads.
- Long content belongs in a doc; post a two-line summary and the link.

## DMs

Use a DM for personal or sensitive matters. Work questions go to the channel, where others can learn from the answer.

## Formatting that renders

- In the Slack composer: `*bold*`, `_italic_`, `~strike~`, `` `code` ``, `>` quote, and typing `* ` or `- ` starts a list.
- `**double asterisks**` show up literally in Slack. Markdown headings (`#`) and tables don't render.
- Text posted through the API uses mrkdwn: links are `<https://example.com|text>`; there is no list syntax, so a `- ` prefix is just text.
- In some draft tools, a digit followed by `)` (like `8)`) turns into an emoji. Write "8." or rephrase.
- Formatting pays only when there is more than a line or two. A two-line message with bold labels reads like a form.
- Bold at most one thing: the headline of an announcement or long update, or the deadline or ask a skimmer must not miss, inside a sentence. Readers treat bold as "this is what matters" and skip the rest, so a second bold weakens the first.

## Length

No credible study gives an ideal Slack message length. Notification previews show roughly the first 50-120 characters (varies by device, unverified), so the point has to be in the first line. Several short messages in a row send several notifications; write one.

## Avoid

- A bare "hi" or "got a sec?"
- Several messages in a row for one thought
- Report headings, bold labels on every line, markdown tables
- @channel or @here for a question
- Chat as the place of record for approvals that need to be found later
- Demanding an instant reply; "ASAP" without a reason
- Bumps with nothing new
- ALL CAPS

## Sources

- nohello.net: https://nohello.net/en/
- Slack, etiquette tips: https://slack.com/blog/collaboration/etiquette-tips-in-slack
- Slack, designing and formatting messages: https://slack.com/blog/collaboration/designing-and-formatting-messages-in-slack
- Slack help, notify a channel: https://slack.com/help/articles/202009646-Notify-a-channel-or-workspace
- Slack help, threads: https://slack.com/help/articles/115000769927-Use-threads-to-organize-discussions
- Slack help, formatting: https://slack.com/help/articles/202288908-Format-your-messages
- Slack developer docs, mrkdwn: https://docs.slack.dev/messaging/formatting-message-text/
- GitLab handbook, communication: https://handbook.gitlab.com/handbook/communication/
- Basecamp, how we communicate: https://basecamp.com/guides/how-we-communicate
