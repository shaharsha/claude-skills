# Partner-mode: writing for an external dev partner

Most design-doc literature assumes the audience is internal — same company, shared tribal knowledge, shared org chart. When the audience is an **external partner** (different company, possibly different stack opinions, possibly competing for credit), several things change. This reference covers exactly what changes.

A textbook partner-mode case looks like this: a customer (call them Acme) hires you to design an AI agent for their product. Acme's existing dev partner (call them Northwind) had pre-pitched the same agent themselves before Acme picked you. Your TDR has to be collaborative-not-replacing in tone, technical but not condescending, and explicit about decision ownership — otherwise Northwind reads it as a takeover and the engagement stalls.

## What changes from a standard RFC

| Concern | Internal RFC | Partner-mode RFC |
|---|---|---|
| **Glossary** | Optional | **Mandatory** — never assume shared terminology |
| **Context section** | 2 paragraphs | 1-2 pages — assume zero shared mental model |
| **Tone** | "Here's the design" | "We're proposing X, here's our reasoning, here are questions for you" |
| **Decision ownership** | Implicit | **Explicit table** — who owns each decision |
| **Stack opinions** | Often skipped | Acknowledge alternatives openly; don't dismiss the partner's stack |
| **Open questions** | Internal team can chat | Numbered, owner-tagged, surfaced as agenda |
| **Pre-meeting protocol** | Loose | Strict — pre-read time, async comment window, agenda |
| **Approvers** | Manager-shape | Both companies — name people, not roles |

## The four partner-mode additions

### 1. Glossary

Place near the top, after Summary. Define every domain term, acronym, and product name you'll use.

```markdown
## Glossary

- **MAU** — Monthly Active Users.
- **Containment rate** — % of conversations resolved without human escalation.
- **MEDLINE** — Acme Holdings's emergency hotline service.
- **RelayHub** — existing Acme chatbot+CRM platform handling WhatsApp routing.
- **Foundry** — Azure AI Foundry, the model-hosting layer used for GPT-5.5 / GPT-5.4-mini.
- **Router** — LangGraph node that classifies which agent (Returns vs Recommendations) handles a turn.
```

The audit script will flag any acronym used >2× without a glossary entry.

### 2. Context section, expanded

Internal context is "you've seen the codebase." Partner context is "you've never opened this codebase." Cover:

- **What the product is.** One paragraph from the PRD/product plan, not the full plan.
- **Where this fits in the existing system.** Which existing services, which existing screens, which existing teams.
- **The user-facing surface.** A mockup, a screenshot, an example interaction.
- **Why this matters now.** Business reason, deadline, dependent commitments.
- **Prior art on each side.** What the partner has built before; what you've built before. Names linked references.

This is the section where you build shared mental model. 1-2 pages is normal. Skimping here costs the entire meeting.

### 3. Decision ownership table

For every decision area, name the owner: *We own / You own / Joint*. This is the section that prevents "we thought you owned that" from surfacing in week 6.

```markdown
## Decision ownership

| Area | Owner | Notes |
|---|---|---|
| Backend architecture (FastAPI + LangGraph) | We propose; joint final | Northwind code review approval required |
| Auth scheme (Acme JWT validation) | You own | We integrate against your spec |
| RN frontend code | Joint | We write the agent UI; you own the surrounding app |
| Deploy pipeline (CI/CD) | You own | We follow your conventions (Azure DevOps? GHA?) |
| Database schema (LangGraph checkpointer) | We propose; joint review | Standard schema; minor extensions our side |
| Pen-testing window | Acme owns (via Acme Holdings) | We schedule via Acme |
| Knowledge / RAG approach | We propose; joint | Decision deferred to v0.2 |
```

Each row: who decides, who reviews, who implements. A blank "Owner" cell is forbidden.

### 4. Tone calibration

Read your draft aloud. If it sounds like *"here's the design, please implement,"* rewrite. The right register is *"we're proposing X based on Y; we'd like your input on Z."*

| Internal-tone phrase | Partner-tone phrase |
|---|---|
| "We will use Postgres" | "We propose Postgres because [reasons]; open to other options if you have strong preferences" |
| "The deploy pipeline is GHA" | "What deploy pipeline does your team use today? We'll follow your conventions" |
| "This is the design" | "This is our proposal — we'd like to walk through the trade-offs and get your input" |
| "Ship by end of month" | "Our internal target is end-of-month; happy to align with your team's cadence" |
| Skip thanks/acknowledgements | Open with one line of context that's collaborative ("Excited to be working together on…") |

The tone shift isn't sycophancy. It's an honest acknowledgement that you can't unilaterally decide things that depend on someone else's stack and team.

## Stack-tension handling

When you and the partner have different stack preferences (canonical example: their team is Node.js, you're proposing Python), don't dismiss their stack. The partner-mode pattern:

1. **Acknowledge openly.** "We know your team is primarily Node.js."
2. **Reason transparently.** "We're proposing Python+FastAPI because [LangGraph maturity, prior art, ecosystem]."
3. **Show the integration boundary.** "The integration is HTTP/REST; most of your team's work stays in Node."
4. **Invite shared ownership.** "We'll write onboarding docs and pair after each milestone so your team can extend the agent in Python."
5. **Name the falsifier.** "If your team has strong concerns about adding Python to the stack, we'd want to hear them before locking in."

When the partner has pre-pitched the same work themselves and the customer subsequently picked you, frame collaboratively — never imply replacement. Acknowledge the partner's prior pitch openly and position your proposal as building on shared ground rather than overruling.

## Pre-meeting protocol (partner-mode is stricter)

- **Pre-read distributed ≥48h before** (vs. 24h for internal). Different time zones, different calendars; people need lead time.
- **Comment window opens immediately** — partner reviewers can leave inline questions before the meeting.
- **Questions doc** as a sibling Google Doc — async comment thread becomes the agenda.
- **Meeting opens with 10-15 min silent re-read** — assume not everyone will pre-read despite the window.
- **Decisions logged at the end** with both-side approvers named.

See [meeting-protocol.md](meeting-protocol.md) for the full meeting workflow.

## Worked example: applying partner-mode to a fresh draft

A typical first-pass partner-mode draft will have the audit flag:

- ❌ No explicit Glossary (terms like "RelayHub," "MEDLINE," "MAU," "Foundry" used inline only).
- ❌ No Decision ownership table.
- ✅ Tone is right (reads like a collaborative proposal, not a directive).
- ✅ Open questions are partner-tagged ("Open questions for Northwind").
- ⚠️ Context is shorter than recommended — could expand the "what fits where" section.

See [examples/standard-rfc-example.md](examples/standard-rfc-example.md) for what a polished partner-mode doc looks like.
