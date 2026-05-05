# Meeting protocol: how the doc interacts with the review

A design doc that lands without a meeting protocol fails twice — once when the doc gets ignored, once when the meeting drags into a third session because nobody pre-read.

## The empirical rule (Nowland, 2018)

| Pages | Pre-read meeting | Format |
|---|---|---|
| 2 pages | 30 min | "narrative review" |
| 6 pages | 60 min | "standard review" |
| > 6 pages | split or → multi-week | hard cap |

These are calibrated for *closing on a decision in one hour*. Past 6 pages, comment volume goes nonlinear and decisions slip a week.

## The 7 protocol elements

### 1. Pre-read window

- **Internal:** distribute ≥24h before the meeting.
- **Partner-mode:** ≥48h. Different calendars, different zones.
- **Async-only / no meeting:** ≥1 week comment window before status flips to Accepted.

The pre-read isn't optional. Authors who say "I'll walk through it in the meeting" are signaling the doc isn't ready.

### 2. Distribution channel

Doc lives in markdown (source of truth) but reviewers comment in the medium they prefer:

- **Google Doc** (most common for partner-mode) — sync via `gdoc-sync`.
- **GitHub PR / Gist** — comments inline, reviews requested formally.
- **Notion** — works for Notion-native teams.
- **Confluence** — corporate-default; most internal RFCs end up here.

Pick **one** primary surface for comments. If you sync to multiple places, comment threads fragment and the doc rots.

### 3. Questions doc (Amazon-style)

Optional but high-leverage. A *separate* doc where reviewers list questions with their name attached. The questions doc becomes the meeting agenda.

```markdown
# Questions for review of design-postgres-migration-v2

## Open questions
1. (@jordan) What's the rollback story if migration takes longer than the maintenance window?
2. (@alex) Will this affect the analytics queries my team runs on the old DB?
3. (@author) Do we need to coordinate with Northwind on the auth schema change?

## Resolved during pre-read
- ~~(@riley) Will the migration affect mobile app behavior?~~ Answered: no, all changes are server-side.
```

Cuts meeting time roughly in half by surfacing the easy answers async.

### 4. Meeting format

| Step | Time | What |
|---|---|---|
| Silent re-read | 10-15 min | Everyone re-reads (or reads, if they didn't pre-read) |
| Walk the questions doc | 30 min | Author addresses each question; reviewers add follow-ups |
| Open discussion | 10-15 min | Anything not in the questions doc |
| Decisions | 5 min | Author names the decisions made; scribe captures them |
| Total | 60 min | for a 6-page doc |

For a 2-page doc, compress: 5 min re-read, 15 min walk, 10 min discussion, 0-5 min decisions = 30 min.

### 5. The 2-round-trip rule (async)

> After two async question/response cycles on a thread, escalate to synchronous.

If you've gone back-and-forth twice on a comment thread without converging, the issue is meeting-shaped. Don't keep typing — schedule 15 minutes.

### 6. Decision capture

Every meeting ends with a list of decisions. Format:

```markdown
## Decisions (2026-05-03)
1. **Migrate to Postgres** — accepted as proposed.
2. **Rollout phases** — accepted with revision: phase 1 is 1 week (was 2 weeks).
3. **Data residency** — deferred to follow-up RFC.

Approvers: Jordan (Acme), Northwind tech lead, [author].
Decision date: 2026-05-03.
Doc status: Accepted (was: In-Review).
```

These decisions get written *back into the doc* (Section 0 status header + decision-log row), not left in meeting notes that nobody re-reads.

### 7. Follow-ups, not approval

Approval is the start, not the finish. Every Accepted doc generates:

- Updated **status** in the header (Accepted, with date and approvers).
- A **decision-log row** appended to `DECISIONS.md` (auto via script).
- Linked **follow-up RFCs/ADRs** for parking-lot questions (each gets its own doc).
- A **first milestone** with date and owner.

If a doc is Accepted with no follow-ups, either it was an ADR (record-only, no work to do) or you missed something.

## Async-only review (no meeting)

Some decisions don't need a meeting:

- ADRs (recording-mode by definition).
- Decisions where the doc + comment thread reaches consensus.
- Cross-team RFCs where everyone's already aligned and just confirming.

Async-only protocol:
1. Distribute the doc.
2. Open a 1-week comment window.
3. Author responds inline to all comments.
4. If no objections after 1 week, status → Accepted; decision-log row appended.
5. If unresolved comments at end of window, schedule a 30-min meeting.

The 1-week window is the magic number — short enough to keep momentum, long enough that everyone has time to read.

## Common failure modes

| Failure | Symptom | Fix |
|---|---|---|
| **No pre-read** | Author re-presents the doc in meeting | Cancel + reschedule with proper pre-read window |
| **Endless meeting** | Doc is too long; can't close in one session | Split the doc; close on sub-decisions independently |
| **Drift** | Decisions agreed in meeting, never logged | Always update Status + DECISIONS.md within 24h of meeting |
| **Approval-only finish** | Doc says "Accepted" but no follow-ups happen | Audit: every Accepted doc should have at least one Next Step assigned |
| **Lost comments** | Comments in Slack, in PR, in Doc, in email | Pick one surface upfront; redirect everything else |
| **Late-breaking objections** | Approver raises objection day-of-meeting that should've been async | Enforce 24h comment window before meeting opens |

## What goes in the doc footer

To bake protocol expectations into the artifact itself, every template ends with:

```markdown
---

## Review protocol

- **Distribute:** ≥24h before review (≥48h for partner-mode).
- **Comment window:** opens on distribution, closes at meeting start.
- **Meeting:** 60 min for this doc length; 10 min silent re-read first.
- **Async escalation:** if ≥2 round trips on any thread, schedule sync.
- **After Accepted:** status updated, decision-log row appended, first milestone scheduled within 1 week.
```

Authors don't have to remember; the doc tells reviewers what's expected.
