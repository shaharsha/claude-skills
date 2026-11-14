# Agent harness patterns

A **task** reference for the prompts and code around a model in an agent or assistant product. It covers:
- when the agent acts and when it asks;
- who can approve what;
- how it waits for work running elsewhere and how it takes steering mid-task;
- how it survives compaction;
- how modes and delegation work and how a goal loop decides it's done;
- how one prompt serves several models;
- how to write the small helper prompts a product needs.

Step 0d sends you here. The provider files still apply inside every prompt; this file covers what holds across providers.

The rules come from two places: production harness prompts (coding agents, chat apps, office, browser, voice and research agents) compared with each other, and vendors' published guidance and open-source harnesses (Anthropic's write-up of Claude Code's auto mode, OpenAI's Codex CLI and Google's Gemini CLI on GitHub). One lesson runs through all of it: a rule in the prompt makes a behavior rarer, while only the harness can rule it out. Put the hard stops in code, and use the prompt to explain them.

## Contents
- Act or ask
- Approvals and authority
- Async work and waiting
- Mid-task steering
- Compaction that doesn't drift
- Modes
- Delegation and subagents
- Goal loops and completion
- One prompt, many models
- Helper prompts

## Act or ask

- **Ask first only when one of two things holds:**
  - you can't name the most likely reading of the request;
  - the task needs something only the user has (a credential, a preference, a fact about their world).

  Otherwise do the work and say which reading you took. A question asked after the work costs the user no extra round trip, and gives them something concrete to react to.
- **Finish what isn't blocked, then lead with what is.** When one part needs the user, do the other parts and open the reply with the blocker, so it gets answered first.
- **Ask for approval of a result, not an intention** (SKILL.md, *Agentic Systems*, the stopping bullet; OpenAI's GPT-6 guidance in `gpt.md`).
- **State your default for a bare request.** Vendors' own harnesses take opposite defaults:
  - OpenAI's GPT-6 guidance treats "can you…" and "I want to…" as instructions to do the work.
  - Google's open-source Gemini CLI assumes every request is an inquiry unless it explicitly asks for action. An inquiry gets an answer or a proposal and no changes.

  A prompt ported between products carries a default that may be wrong for its new home, so write yours down.
- **Name the reversible set as well as the dangerous one.** "Edits in the working tree, read-only commands and local tests need no approval" prevents more needless pauses than any "be autonomous" line. It also gives the dangerous list a clear edge.
- **Lower effort shrinks thinking, not scope.** At low effort some models finish less of the request (`claude-sonnet-haiku.md`). Fix it with finishing text and a stated end point (SKILL.md, *Agentic Systems*, the stopping bullet), not by raising effort everywhere.

## Approvals and authority

- **Write down three tiers:**
  - actions the agent never takes, even when asked (for example permanent deletion, changing who can see or edit something, purchases or trades, creating accounts; pick yours);
  - actions that need an explicit go-ahead;
  - everything else, which is free.

  Most prompts write only the middle tier, which leaves the model guessing at the other two.
- **Consent covers one action and its blast radius.** Anthropic's write-up of its auto-mode classifier (*How we built Claude Code auto mode*, anthropic.com/engineering) gives the cases:
  - "clean up my branches" doesn't authorize a batch delete;
  - "can we fix this?" is "a question, not a directive";
  - "Clean up the PR" doesn't name a force-push;
  - an earlier approval of a similar action isn't a pattern.

  Write the rule so an approval names the dangerous part (the target, the remote, the production flag), not only the goal. OpenAI's open-source Codex review prompt adds two more: urgency doesn't change authorization, and wanting an end state doesn't authorize every action that would reach it. For how specific a go-ahead a model needs, see `claude-fable.md` (*Approvals are applied as written*).
- **Say which channels can authorize.** Permission can come from:
  - the user;
  - the developer;
  - project instruction files;
  - the product's ask-the-user tool.

  These sources can only inform:
  - tool output and retrieved documents;
  - skill text;
  - messages from other agents;
  - documents under review;
  - the agent's own earlier text.

  This holds even when the text in them looks like the user speaking. The user can extend trust to named content ("follow the steps in this ticket"), but untrusted content can't widen what was approved; Codex's review prompt draws exactly this line. A reminder that loosens a rule is suspect, because real harness reminders tighten.
- **A denied call means adjust, not retry.** Tell the agent that a denial is a boundary: find a safer path or ask, and never repeat the call or reach the same effect another way.
  - Anthropic returns each denial as a tool result carrying that instruction. After 3 consecutive or 20 total denials it hands the session to a human; a headless run ends instead.
  - Gemini CLI tells its agent not to re-attempt or negotiate a declined call.
  - Codex tells its agent not to "circumvent approvals by using other tools".
- **Name the bypasses you mean.** "Don't work around restrictions" is too vague to follow, so list them:
  - writing to the file or state a check reads;
  - spoofing an identity;
  - probing local services;
  - editing tests or graders;
  - retrying with a skip-verification flag;
  - searching config for another credential after an auth error.

  The last two are among the overeager actions Anthropic's classifier blocks.
- **Credentials never pass through the model.** The user types them, a vault fills them, or the product hands control to the user. The agent never sees or relays them.
- **The prompt makes a behavior rarer; the harness prevents it.** Anthropic reports that its classifier misses 17% of real overeager actions. It found no prompt fix for the hardest part, judging whether a consent covers this action's blast radius, "that doesn't cost more than it gains". Keep irreversible actions behind gates in the tools (SKILL.md, *Agentic Systems*, *Autonomy calibration*). `evals.md` (*Gate classifiers and action reviewers*) covers building the gate.

## Async work and waiting

- **Say how completion arrives, and that there's no need to poll for it.** Some results report back on their own:
  - a notification or a wake-up from a background job;
  - a result returned against the original `call_id` (OpenAI's async tool calling, `gpt.md`);
  - a message from an async subagent (`langgraph.md`).

  Tell the agent which one applies, and that it shouldn't check in a loop. An agent nobody told will poll, and each poll costs a turn and fills context.
- **Poll only what can't notify, at the rate it changes.** For external state with no notification (a CI run, a deploy, a queue), give a check interval tied to how fast it moves. Codex's persistent mode prefers a completion notification or the product's wait mechanism. Failing those, it checks active near-term work every 1-3 minutes and backs off when progress is slow.
- **A pending result is never the answer.**
  - The agent doesn't invent a result it hasn't received.
  - It doesn't treat "still running" or an unchanged status as done.
  - It doesn't read elapsed time as approval.
- **No promise without a mechanism.** "I'll let you know when it finishes" is false unless something is scheduled to check. Either schedule the check or tell the user how to find out.
- **Keep the wait in state.** Record the target, the last known state, the stopping condition and the next check wherever the harness keeps task state, so the wait survives a context reset (Codex's persistent mode).

## Mid-task steering

- **A new message steers the task; it doesn't replace it.** Apply the smallest change the message asks for, keep the work it doesn't touch, and drop work only when the user cancels it explicitly. Without this rule, agents abandon half-finished work to chase the newest message.
  - Gemini CLI treats a hint the user sends during a run as a "scope-preserving" course correction.
  - OpenAI's API supports the same flow as mid-turn steering (`gpt.md`).
- **Say which messages end the task.** Name the explicit stop or cancel your product recognizes, and treat everything else as steering.
- **Preferences hold for the task.** When the user sets pacing, verbosity or how often to update, keep it for the rest of the task, across later turns and background updates. Codex's voice front end treats these as task-level preferences.
- **How you deliver the message matters on injection-hardened models.** Send the user's mid-run words as a user text block after the tool results (SKILL.md, *Context Engineering*, the append-only bullet).

## Compaction that doesn't drift

SKILL.md (*Context Engineering*) covers when to compact and why compaction notes steer every later window; `claude-fable.md` has Anthropic's keep-list for Fable 5.2. The rules below are for the summarizer's own prompt.

- **The summarizer treats the history as data.** Tell it to ignore instructions found in the conversation and to stay in its output format; Gemini CLI's compression prompt opens with this. Say "no tools" at the start and again at the end of the prompt: a summarizer that calls a tool returns no summary.
- **Keep the user's words where wording matters.**
  - Carry every active request and constraint forward faithfully, in the user's own words when the exact phrasing matters; paraphrase is where a requirement quietly changes.
  - For a long specification, keep a pointer to the original (a file, a message) rather than a summary of it.
  - Drop requests that are done or replaced.
  - Keep each decision with its reason, and record what was ruled out.
- **Separate done, in progress and to do, and mark the current focus.** Gemini CLI's snapshot has these parts:
  - a task list marked DONE / IN PROGRESS / TODO, with the current focus;
  - the active constraints;
  - an artifact trail: what changed and why;
  - the recent actions;
  - when an approved plan exists, the plan's path and each step's status.
- **The resumed agent checks before it trusts.** Tell the next window to inspect the current files and state before acting on the summary. Codex's goal loop treats the working tree and external state as authoritative and earlier context only as a pointer.
- **Skip the written scratchpad on thinking models.** Some compaction prompts ask for an `<analysis>` or `<scratchpad>` block before the summary. On models that think natively that repeats work, and on Claude Opus / Sonnet / Fable 5.x a request to write reasoning out can be refused as `reasoning_extraction` (`claude.md`).

## Modes

- **Define a mode by what it may change.** Codex's open-source plan mode lists what is allowed and what is not:
  - allowed: reading, searching, static analysis, and tests that write only to caches;
  - not allowed: editing files, formatters that rewrite them, migrations, and side effects that carry out the plan.

  It adds a tie-breaker: if an action "would reasonably be described as 'doing the work' rather than 'planning the work'", don't take it. A mode defined by intent ("think, don't act") leaks.
- **Name who can switch it.** In Codex only a developer message changes the mode; user requests and tool descriptions don't. A user who asks for execution while in plan mode is treated as asking to plan the execution. Products differ, and some switch on an explicit user command, but write the rule down. Otherwise a user's "just do it" ends the mode by accident.
- **Enforce the mode in the harness.**
  - Make the tools a mode forbids return an error when called in that mode. Keep the declared tool list the same across a mode switch: editing it mid-conversation restarts the prompt cache on every provider, and on Claude 5.5-generation models it invalidates earlier thinking (SKILL.md, *Context Engineering*, the append-only bullet). Withhold tools only when the mode is fixed for the whole conversation.
  - Give each mode an exit: an approve-plan tool, or a plan block the client renders.
  - Name the ways a turn may end in that mode. Codex's plan mode allows one complete plan block per turn and no "should I proceed?", because the user can leave plan mode themselves.
- **Explore before asking.**
  - Never ask the user a fact the agent can find (where a struct lives, which component exists).
  - Ask about preferences it can't find out early, as 2-4 options with a recommended default.
  - If the user doesn't answer, proceed with the default and record it as an assumption (Codex's plan mode).
- **A mode classifier needs a default class.** When a router picks the mode (chat, do, plan), give it the class to choose when unsure. Pass the user's exact words, not a paraphrase, to the agent it routes to.

## Delegation and subagents

SKILL.md (*Agentic Systems*) covers when to split, fork vs isolate, and the four parts of a delegation (objective, output format, tool and source guidance, boundaries). Production briefs add:

- **What's already ruled out**, so the worker doesn't check it again.
- **Read or write:** whether the worker may change anything, and which files are its own.
- **A length cap for the reply.** For a lookup, give the exact command to run; for an investigation, give the question to answer.
- **Never delegate understanding.** A brief that says "fix the bug you found" or "based on your findings, implement it" hands over a diagnosis the worker never saw. Write the diagnosis into the brief, or do that step yourself.
- **Verify the result against an outside record.** A worker's summary says what it meant to do. Check the diff, the file, the test output or the state before reporting the work done, and never fill in a result that hasn't arrived.
- **No two writers on the same files.** Gemini CLI forbids parallel subagents whose abilities change the same files or resources, and allows parallel research and read-only work.
- **Authorization doesn't pass by delegation.** Inside a subagent, the orchestrator's instruction looks like the user's, so a task the user never asked for looks fully authorized. In Anthropic's auto mode the subagent's own tool calls go through the same gate, plus two checks at the hand-off:
  - at delegation, where the check can deny a task the user never asked for;
  - at return, where it reviews the subagent's actions and warns the orchestrator, because content the subagent read may have compromised it mid-run.
- **Wait for running workers before ending the turn.** If the user asks a question meanwhile, answer it, then keep coordinating (Codex's orchestrator prompt).

## Goal loops and completion

For agents that keep working across turns toward one goal (an automatic "continue" loop), the goal prompt in OpenAI's open-source Codex is a good model:

- **Label every previous turn** with one of three labels:
  - progress: state changed, work was completed, or new evidence changes the next action;
  - a verified wait: polling a specific job or handle that is confirmed live now;
  - no progress: a status recap, or a plan that wasn't carried out.
- **"Blocked" needs a repeated blocker.** When a real blocker appears, report it and take any other safe action, but leave the goal open. Mark the goal blocked, a status that ends the loop, only after the same blocking condition holds for 3 consecutive turns, and count a reworded blocker as the same one. Never mark it blocked because the work is hard, slow or uncertain.
- **No narrower substitute.** Don't swap in a smaller, safer or easier-to-test solution because it passes the current checks. An edit is aligned only if it makes the requested end state more true.
- **Run a completion audit before claiming done.**
  - List each requirement, named file, command, test and deliverable.
  - For each, find the evidence that would prove it, and check that evidence in the current state.
  - Count weak, indirect or missing evidence as not done.
  - A check narrower than the claim doesn't support the claim.
- **Budget isn't completion.** Never close a goal because its token budget is nearly spent; report the budget and the remaining work instead.

These sit on top of SKILL.md's stopping rules (*Agentic Systems*: define done, keep a checklist). SKILL.md's cap of 2-3 continuation messages is for nudging a run that stopped early with no stated blocker. A goal loop that shows verified progress each turn keeps going; apply the cap to turns without progress.

## One prompt, many models

- **One shared core, small per-model deltas.** Products that serve several models keep one prompt and add a short section per model; OpenAI's Codex repository carries a prompt file per model family. These deltas earn their place:
  - finishing and stopping text;
  - memory hygiene;
  - the edit tool and its format;
  - channel and formatting rules;
  - patches for failures seen on that model.

  Everything else stays shared.
- **Each model gets the finishing text for its own way of stopping early.** Anthropic publishes a different block per model:
  - Fable 5.2's *Finishing work* block (`claude-fable.md`);
  - Opus 5.5's paragraph for unattended agents (`claude-opus.md`);
  - the block for Haiku 5.5 and for Sonnet 5.5 at low effort (`claude-sonnet-haiku.md`).

  Small models and low effort need the most explicit version. Scaffolding written for a small model can overconstrain a large one that reads the same core (SKILL.md, *Budget Models*). LangGraph's per-model harness profiles are one way to hold the deltas (`langgraph.md`).
- **Give long-tail models a generic template.** Models you don't tune get the shared core and the safest defaults. Tune a model only once you have its failures in front of you.
- **Change by adding a variant, not by editing the core**, and have each patch name the shared rule it overrides: SKILL.md, *Process* (*Maintaining a prompt in production*).

## Helper prompts

The small prompts around an agent fail in their own ways. They include conversation titles, summaries, suggested next messages, answers to side questions, and advisors.

- **Give a numeric budget and a format that fits where the output appears.** A title is "3-7 words, no punctuation"; a suggestion is whatever fits on a button.
- **Make "none" a valid output for optional helpers.** A suggestion or memory-extraction helper told to always produce something will invent something, so make the empty answer explicit and the default. A summarizer whose output carries the task forward always produces its summary.
- **Tell it what it can't do.** Tell a side-question helper with no tools that it has none, or it will promise to look things up.
- **Advisors give a check, not a verdict.** An advisor model consulted mid-task should:
  - say which stage it thinks the agent is at (starting, stuck, reviewing, choosing);
  - offer the check that would settle the question;
  - say whether a concern blocks the work or is only advice.

  Advisory text steers strongly (SKILL.md, *Agentic Systems*, *Advisory agents steer expert judgment*).
- **Action classifiers** are helpers that return a verdict: see `evals.md`, *Gate classifiers and action reviewers*.
