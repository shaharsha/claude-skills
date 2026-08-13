# Input to the next governance audit — 2026-08-12

**This is a WORKLIST, not a handover and not governance.** Nothing here is in force. It exists because
these findings were produced in one evening across four sessions and would otherwise die in message
history — the same failure `/dispatch` now warns about: *a lane that ends without warning ends with
your only copy.*

**Delete this file once its contents have been folded in or rejected.** A worklist that outlives its
pass becomes a second source of truth, which is the defect half of tonight was about.

---

## A · Findings not yet in any file

**1 · A TRANSCRIPT CONTAINS ITS OWN SOURCE, so a content-match over it counts DISCUSSION as ACTION.**
Asked whether it had ever run `/pr`, a lane's first probe returned **1 hit — its own grep command**,
echoed into the transcript by the search run to answer the question. Another went `17 → 8 → 5`
(mentions → command-shaped text → executions). **The discriminator is EXECUTION vs MENTION:** tool_use
inputs, and within those, a line that *begins* the command.

⚠️ **This trap points the opposite way from the five silent zeros, and both are under-scrutinised:**

```
silent zeros      returned the REASSURING answer     nobody re-checks a clean result
transcript trap   returned the ALARMING answer
                  ABOUT YOURSELF                     nobody re-checks that either — doubting it
                                                     looks like self-exculpation
```

**The measurement created the thing it measured.** A lane would have reported a merge it never made,
and no reviewer would have questioned it.

**1b · FOUR INSTANCES OF THE TRANSCRIPT TRAP IN ONE EVENING, AND THE FOURTH IS THE TELL.** The
coordinator committed it **ten minutes after writing it to memory**, in the same command where it was
correctly using the registry: `grep -l "9a4d9e" *.jsonl` matched **its own transcript**, because it had
just pasted that ref into it. *"The registry read carried the answer; the grep was noise I would have
believed if the registry had been ambiguous."*

⚠️ **Three separate tools needed the SAME execution-vs-mention discriminator on the same evening,
each discovered independently:** the lanes auditing their own transcripts, `ccverify`'s `NOT TOUCHING`
parse, and `ccdoccheck` telling a retired tool narrated in prose from one named in a bash fence. **One
distinction, three discoveries, no transfer between them** — which is itself the *"a rule stated at the
level of a MEDIUM does not generalise; state it at the level of the MECHANISM"* finding, arriving again.

**1c · A POSITIVE DATA POINT ON RULE SHAPE, worth recording because they are rarer than failures.**
*"Identify by MECHANISM, not by recency or name"* was written into `/dispatch` after the coordinator
mis-identified two adjudicator sessions. **Within the hour it fired on its own author, in a different
seat**: told two unidentified sessions had appeared, its first action was the registry rather than a
message, and nothing was chased.

🔑 **Note the shape — it is consistent with the prose-that-works theory.** *"Go read the identifier you
already hold"* tells you to PRODUCE AN OBSERVATION. It is not *"do not confuse sessions."* That is one
data point, not a result, and it belongs beside the four failures rather than instead of them.

**1d · AN ORDINAL IS NOT AN IDENTIFIER — and this is the fourth address-shaped failure of the night.**
Two lanes sent eight-item reports the same evening. **Both contained the hard-bar finding — one as #4,
the other as #7.** A reply written in one lane's numbering was read by the other against its own list,
which recorded a finding as simultaneously acted-on and deferred.

⚠️ **The cross-reference was CHECKED, was CORRECT, and still misled** — because the referent was a
different document of the same shape. A number is only an address if you name the list.

```
a bare session name    resolves — to nobody, or to somebody else
a stale ref            resolves — and reads exactly like a dead lane
a recency match        resolves — to the newest thing, not the thing you made
an ordinal             resolves — in whichever list the READER is holding
```

**All four resolve to something. None of them resolves to what you meant.**

🔴 **AND THE OBVIOUS REMEDY — "use stable session ids" — HAS THE SAME DEFECT ONE LAYER DOWN. THERE
ARE TWO ID REGISTRIES AND THEY DISAGREE:**

```
~/.claude/sessions/*.json     ccpeers · ListAgents · SendMessage          one UUID
Desktop session registry      list_sessions · set_session_title ·
                              ccd_session_mgmt__send_message              a DIFFERENT UUID
```

Measured: the adjudicator is `509b8ecd` in the first and `3c2948a5` in the second. A `SendMessage` to
a Desktop-side id returns **`success:false — no agent by that name is reachable`**, which reads exactly
like a dead session; the same id delivers fine through `ccd_session_mgmt__send_message`.

**So the rule is "use stable ids AND say which registry's id it is."** ⚠️ And note where this bites:
`set_session_title` needs the Desktop id, so the *"Session not found"* it returns for a messaging-side
id is a wrong-registry error wearing a missing-session error's clothes.

**1e · 🔑 A PROCEDURE VALIDATED ON THE EASY HALF OF ITS OWN POPULATION — three instances, three
tools, one night.** The documented session-rename recipe said *"try the real id first, never look one
up by title."* It was written from sessions whose two registries happened to agree, so the shortcut
worked — **and it fails precisely on the sessions Desktop did not create, which are the ones most
likely to need renaming.** The validation set and the use case were disjoint, and nothing in the note
said so.

⚠️ **Following it correctly produced a user-visible defect** — a second sidebar row for a live session
— which is worse than a gap: an instruction that reads as settled, is never audited because it looks
settled, and does damage when obeyed. Same class as `/pr`.

```
the rename recipe        validated where the ids matched; needed where they do not
_ACCEPTANCE_TARGETS      a gate whose corpus cannot reach the case it exists for
a coverage test          bounded by the corpus it was measured on
```

**The line: when a procedure works "usually", ask WHICH HALF of the population it was validated
against, and whether the hard half is the one that needs it.**

**1f · A CORRECTION IS A CREDIBILITY MARKER, AND IT LAUNDERS WHATEVER SURVIVES IT.** The rename note
had been corrected once already — it repaired a false *capability* claim and left a false *diagnosis*
inside the fix. **A file headed "⚠️ THIS WAS WRONG. Corrected." invites the reader to trust everything
after that heading.** The note has now been wrong in two different ways about the same tool.

🔑 Same shape as *"a caveat on the right sentence makes the uncaveated ones look checked"*, which this
file already carries — **applied to one's own corrections rather than to prose written for others.**

**1g · 🔑 A SESSION CANNOT OBSERVE ITS OWN IDENTITY IN THE DESKTOP REGISTRY. THE SPLIT IS ONLY
MEASURABLE FROM A SECOND SESSION.**

```
list_sessions            EXCLUDES the current session, by contract
the derived Desktop id   never appears in ~/.claude/sessions, BY CONSTRUCTION
```

**So from inside, both halves of your own identity are unobservable.** A lane grepping
`~/.claude/sessions` for its own Desktop id gets ZERO — correctly, and it *could never have been
anything else* — which is exactly why it reads as *absence* rather than as *derivation*.

⚠️ **This generalises a rule the preamble already carries one field over:** *"you cannot observe your
own idle time — you are structurally the wrong instrument."* Same shape, different attribute. **Who can
verify a claim is a property of the claim**, and for identity the answer is: not you.

**Consequences measured the same evening, both from the inside-vantage:**

```
a lane concluded its two registries AGREED    from a list_sessions row that, by that tool's own
                                              contract, could not have been it
this session asserted its own Desktop id      in messages, for hours — and it was the DEPRECATED
                                              entry. local_0b3c1d9a isRunning:false;
                                              local_874e6c07 isRunning:true was the live one
```

🔑 **A message asserting its own identity was less reliable than the envelope that carried it** — and
the correct resolution is the counter-intuitive one: **trust the provably-live sender over the
self-declared id.** State it that way round, because the instinct is the opposite.

**1h · THE FOURTH ADDRESS FAILURE IS DIFFERENT IN KIND FROM THE OTHER THREE.**

```
ordinal              resolves — wrong referent          } ambiguous ADDRESS
bare name            resolves — wrong live process      }
id → wrong session   resolves — wrong session           }

TITLE JOIN           the key was FINE. The FIELD is not shared across the two registries.
```

**The first three are ambiguous addresses; the fourth is a join on a column that only looks common** —
and it fails **silently, as absence**, which is the direction that gets acted on. It produced real
consequence: a lane was told `SendMessage` would not reach it, from a lookup structurally incapable of
finding it.


**1i · SIX FINDINGS REPORTED BY LANES THAT REACHED NO FILE UNTIL 2026-08-13.** Recorded late, and the
lateness is the point: I told a lane I was *"carrying #3 into the worklist now"* and then did not, for
four hours, while writing tools whose purpose is that findings not die in messages.

**a · A MONITOR VERDICT IS NOT ATOMIC, and the failure DIRECTION is the finding.** Monitor batches
stdout within ~200ms, so a composed verdict splits across events: a header arrived with `JOBS:` empty
and the eight job rows came in the NEXT event, producing a false alarm about a zero-job run — the one
condition that check exists to detect.

🔑 *"Mine split ALARMINGLY, so I went and measured. Split the other way — rows present, conclusion lost
— it reads clean and nobody looks."* **Every batching boundary has a safe direction and a silent one,
and only one of them gets investigated.**

**b · THE DOCUMENTED "NOTHING RAN" SIGNAL HAS A FALSE POSITIVE.** The rule is that an EMPTY JOB LIST
proves a CI run did nothing. Measured: it returned empty as a *batching artifact* while both jobs had
succeeded. Re-queried as one read: 2 jobs, both success. ⚠️ **The authoritative NEGATIVE signal can lie
in the alarming direction** — which is the half nobody re-checks, because doubting an alarm about your
own work looks like self-exculpation.

**c · `gh pr checks` IS HEAD-AGNOSTIC.** It reports whatever the PR's CURRENT head has, so a monitor
armed before a push emits `pass` events indistinguishable from the live one's. **Remedy: read head and
checks in ONE call** — `gh pr view --json headRefOid,statusCheckRollup` — because two reads can straddle
a push. Same shape as the stale tree: a status true about a different revision than the one asked about.

**d · A SESSION CANNOT RENAME ITSELF.** `set_session_title` refuses the current session BY DESIGN, so a
lane advertising state in its title depends on a third party to keep it true. **Titles are therefore
STRUCTURALLY guaranteed to go stale, not incidentally** — which is why a dispatcher resolving a lane by
title got `TOR-467 / #523` for a lane holding `TOR-567 / #527`, from a registry, reading as more
authoritative than a guess.

**e · A SKILL'S ADDRESS EMBEDS A PLUGIN VERSION THAT ROTS WHILE THE SKILL DOES NOT.**
`b29e7cf65e5c:pptx` and `f17010c9bb48:pptx` are the same capability; both version directories sit on
disk with identical skill sets. **A dead prefix therefore looks PRESENT to a filesystem check while
being unaddressable** — worse than a clean absence. Measured clean across four instruction populations,
so the trap is armed and unstepped-on. ⚠️ `ccdoccheck` does not cover skills; deliberately not built,
because a gate for zero current exposure is how gates become noise.

**f · `CLAUDE.md` IS RE-INJECTED IN FULL, REPEATEDLY, ON FILE-TOUCH.** A lane observed the same large
payload arriving many times in one session. **Not measured from inside and not verified by me** — stated
as an observation with its provenance, not a finding.

**2 · WHEN TWO PROBES DISAGREE, ASK WHAT EACH IS A FACT ABOUT — not which is right.**
`17`, `8` and `5` were **all three correct**. Nothing was broken; three different questions were being
answered and only one had been asked. This is stronger than *"treat any gap as the instrument"*,
because it converts a disagreement from an error to resolve into information to attribute.

**3 · A FILE THAT INSTRUCTS IS A FILE WITH AUTHORITY, WHATEVER IT LOOKS LIKE.**
`/pr` — 284 bytes, generic voice, no dates, no incident log — said *"once all checks pass, merge the
PR."* No approval, no round, no re-merge. It sat in the command namespace all sprint and **was never
audited because it failed the pattern-match for "governance file."** The audit followed the shape of
the artifacts rather than the shape of the authority.

**4 · A SILENT INSTRUMENT LOOKS IDENTICAL WHETHER IT WAS BLIND OR SATISFIED.**
*"In both cases the green is real and the inference is the defect. CI genuinely passed; the acceptance
run genuinely found no difference. Nothing is broken, no check misfires — and that is exactly why
neither leaves an artifact."* **A `/pr` merge and an adjudicated merge are indistinguishable in git:**
same author, same green, same merge commit. No artifact separates them, so only asking can.

**5 · STATE CLAIMS EXPIRE, AND THE DECAY IS INVISIBLE.** Derived independently three times in one
evening, from three different accidents:

```
a gap someone reported about THEIR OWN work is the class most likely to have been closed since
a relayed state claim needs a TIMESTAMP           (a 15-min-old report of a 30-second gap)
"X does not exist" has an expiry                  (a note true when written, false 16 min later)
```

**A stale state-claim and a wrong state-claim read identically later.** The actionable half:
**record the timestamp of the check beside the claim**, so the next reader sees expiry rather than
guessing at fault. ⚠️ **These three are currently scattered as half-rules in three files** — which is
itself the two-places defect forming in real time. One rule, one home.

**6 · A CORRECTION YOU ACCEPT BECAUSE CORRECTIONS HAVE BEEN ARRIVING IS ONE YOU DID NOT CHECK.**
A session nearly filed a *correct* note as an error: *"I reached for 'I was wrong' because a peer had
just corrected me twice and a third seemed to follow. That is inference from social position, not from
evidence — the same shape as complying on tone."*

**7 · A WRONG HARD BAR CONVERTS A CORRECT RESULT INTO EVIDENCE OF FAILURE — in the direction the
author already expects.** A lane was given *"all four silent differences are text nodes; finding three
means the instrument is BROKEN, not partial."* Three of the four had been observed directly. The
fourth sat beside them and was **carried by them**. Measured: 9 marker paths vs 0 dots, **zero
characters of text on either side.** So a correct instrument scoring 3/4 was defined as broken.

🔴 **And the natural repair MANUFACTURES the defect** — widen the extractor until something near the
dots yields a string, and now you have a difference that was never there. The lane avoided it only by
having measured the mechanism first.

**Proposed rule, and it is a good one:** *a DONE-WHEN may only cite criteria the author has personally
observed. Anything else is labelled **"predicted — verify before relying."*** Note this is the
laundering rule (§"A TRUE MEASUREMENT LAUNDERS THE UNTESTED CLAIM BESIDE IT") arriving in a new
place: **three observed criteria lent their authority to a fourth nobody had looked at.**

**8 · PERISHABLE EVIDENCE HAS NO HOME, and its expiry is silent.** A measured difference stopped being
reproducible the moment its slot was re-projected — published bytes are immutable, but the *comparison
partner* is regenerated. It survived as a fixture only because a warning happened to appear in an
unrelated paragraph. **Nothing in the process asks "does this evidence expire?"** Same family as §5
above, one layer down: not a claim that goes stale, but the ability to re-take the measurement at all.

**9 · RELAY DEGRADES CLAIMS, IT DOES NOT ONLY DELAY THEM.** Of four figures handed to one lane as a
starting point, **three were wrong** — and the dangerous one named a page that does not exist while
carrying a chart count that was **correct for a different page.** ⚠️ **A wrong subject with a right
number passes every spot-check downstream, because everything downstream of the number works.**

Also measured twice in a single lane: hub topology **manufactures** stale state — the coordinator held
*"next: all four or the instrument is broken"* while the lane had already run it and reported 3 of 4,
and a correction crossed a result an hour later. When they finally went lane-to-lane at the moment of
exposure, a shared-reduction problem took **two messages that had taken four through the hub.**

**10 · A CONTROL THAT RUNS IS NOT A CONTROL THAT DISCRIMINATES.** Four gates built that evening were
defective on first use, **all by careful people, and every one executed successfully and reported
confidently**:

```
ccverify, run bare        measured the MAIN CHECKOUT (empty range) -> reported untracked scratch
                          as the PR's diff, printed "THE PLAN FAILED"
ccverify, the parse       read backticked prohibitions as DECLARATIONS
reviewDecision            EMPTY on all 30 PRs ever checked — adjudications live in issue comments.
                          ⚠️ AND EMPTY READS AS "NOTHING BLOCKING", SO IT FAILS OPEN. Written into
                          /dispatch by the session fixing the withdrawal incident, in a section
                          about controls, and caught by a lane within the hour.
a lane's own guard        wrong four times before it was right (hand list -> direct-call ->
                          bare-name -> functions-only). Final closure: 29.
```

**Green output is the default failure mode of a gate, not the exception.** Every new gate needs a
must-fire demonstrated **against the real gate**, not against a re-implementation of its logic — one
lane's mutation tests re-implemented the comparison instead of invoking the shipped assertion, and a
reviewer caught it.

**11 · PLAN MODE IS STRUCTURALLY UNUSABLE FOR AN UNATTENDED AGENT.** `ExitPlanMode` is the *user's*
approval gate — **no peer can press it.** A lane that enters plan mode while the human is away is
stranded holding a finished plan it cannot act on. The process said *"plan first"*, which lanes read
as *"enter plan mode"*.

🔑 **Generalise: any process step whose EXIT condition requires the human is a deadlock for an
unattended agent — and the instruction naming it reads as sanctioned.** Check exit conditions for
reachability, not just entry conditions.

**12 · WHEN YOU SPLIT A SEAT, ENUMERATE THE MESSAGE *PRODUCERS*, NOT THE MESSAGE *KINDS*.** The
published routing rule — *rulings → adjudicator, state → dispatcher, completions → both* — covered
everything **lanes** send and nothing the **seats** send. An approval withdrawal is state that
originates at a seat, and the uncovered producer fed the merge button.

**13 · A STATE CHANNEL NOBODY CAN WRITE TO THEMSELVES WILL BE STALE.** Titles became the channel for
what git cannot show (unpushed shas, held work) — and `set_session_title` **refuses the current
session**, so a lane cannot maintain its own. One advertised `de4f9c1 unpushed` well after it was
pushed and merged. ⚠️ **A stale title is read by a sweep that is specifically NOT checking** — that is
the whole reason the channel exists, so there is no second source to disagree with it.

**14 · NOTHING TESTS THAT AN INSTRUCTION'S NAMED TOOLS EXIST.** *"The cheapest possible check to
automate, and it was absent."* Three `ccsend` references survived its retirement inside the preamble,
one of them naming it as the only permitted plan-mode channel.

**15 · SMALLER, MEASURED, ALL PURE TAX:**

```
bare-name refusal          every FIRST send to a peer costs two calls, and refs cannot be cached.
                           ⚠️ The cost lands on exactly the behaviour we want more of —
                           lane-to-lane traffic that does not route through the coordinator.
file locking               a CONVENTION, not a mechanism. Two lanes nearly edited ChartView.tsx
                           simultaneously; prose announcement is all that prevented it.
                           Proposed: .claude/leases/<path> = <session>, checkable with cat.
Codex PLAN rounds          review the SANDBOX unless framed — one round returned 2 HIGHs, both
                           about its own environment ("invalid auth", "read-only workspace"),
                           zero about the design. Belongs in the template, not each prompt.
fresh-worktree setup       no node_modules, no .venv, npm ci per worktree, baseline artifacts do
                           not cross. A fresh branch reports "698 missing", which reads as data loss.
gate stack vs blast radius EIGHT gates for a one-line JSX prop. The stack is uniform; the changes
                           are not.
notification truncation    previews cut near 3000 chars and a truncated instruction reads as whole.
                           The convention that saved it: senders writing "READ THE FULL TEXT AT
                           <path> BEFORE ACTING".
```

---

## B · Structural defects found by reading, still open

**§4 of `LANE-PREAMBLE.md` says "this is the section that matters" and it is no longer true.** Most of
the instrument material now lives in the ~800 unsectioned lines after §8 — the wrapper rule, the
uniform-output-column rule, the one-axis-control rule, the laundering rule. A lane taking §4 at its
word reads the section that matters and stops before the majority of it.

**The tail has been consolidated before and left its sources in place.** *"A WRAPPER'S STATUS IS
TRUTHFUL ABOUT ITSELF"* opens by saying it "unifies four rules this file carried separately" — and at
least the pipeline case is still separately present in §4 and §6.

⚠️ **Both are the same class as the sum/partition contradiction fixed tonight: the file has been
edited by ADDITION and never audited as a whole.** A file that can only be audited by reading all
1,400 lines has no audit — the two contradicting entries shared no vocabulary, so every grep aimed at
exactly that class went straight past them.

---

## C · Open questions that are decisions, not defects

```
seat singularity has no mechanism        two adjudicators existed 26s apart, neither aware.
                                         "I read the criteria and announced myself" is the whole
                                         of becoming one.

"one ruling per invocation" is           a peer seat is long-lived by construction, so the rule
unenforceable in a long-lived seat       reduces to self-discipline — and the instruction itself
                                         concedes "a polluted adjudicator looks exactly like an
                                         efficient one." Proposal on the table: spawn the peer
                                         seat per question too, and delete the unenforceable line.

the approval pair has no fixed point     12-minute CI against three merging lanes. A procedure
on a busy develop                        exists now (APPROVAL-CRITERIA §5) but there is still no
                                         merge-window RESERVATION anywhere in the architecture.

APPROVAL-CRITERIA.md is untracked        `~/.claude/torque-orchestration` is a symlink into
                                         ~/Projects/claude-skills, which IS a git repo.
                                         LANE-PREAMBLE is tracked; this file was never `git add`ed.
                                         One command fixes it — Shahar's call, his published repo.
```

---

## D · Residual risk from the `/pr` near-miss

**No lane that can be questioned ever ran it.** Three lanes measured their own transcripts: zero
invocations, twelve merges all explicitly hand-typed.

⚠️ **That is a bound on the POPULATION, not on confidence.** A session that has ended cannot be asked,
one ended that evening, and nothing on disk distinguishes its merges from any other's. One lane is
measuring the approval provenance of four earlier merges (`#446 #503 #506 #512`) it declined to vouch
for from memory — *"I would be reconstructing from a long context rather than measuring."* That result
is the last open item.
