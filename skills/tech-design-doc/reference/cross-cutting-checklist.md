# Cross-cutting concerns: the checklist

Cross-cutting concerns are the easy-to-forget axes. The strongest design docs — Kubernetes KEPs in particular — operationalize them as a *fixed checklist* nobody can hand-wave through. This skill borrows that pattern.

## The rule

> Every item in the checklist is filled in. Skipped items are explicitly marked **N/A** with a one-sentence reason. Silent absence is forbidden.

Why: silent absence is what causes "oh, we forgot about observability" to surface in week 6. Forcing each line — even with N/A — forces a structured pass.

## Standard checklist (4-6 page doc)

```markdown
## Cross-cutting concerns

| Concern | Status | Notes |
|---|---|---|
| **Security** | ✅ / ⚠️ / N/A | … |
| **Privacy / PII** | ✅ / ⚠️ / N/A | … |
| **Observability** | ✅ / ⚠️ / N/A | … |
| **Rollout / Rollback** | ✅ / ⚠️ / N/A | … |
| **Scalability** | ✅ / ⚠️ / N/A | … |
| **Dependencies** | ✅ / ⚠️ / N/A | … |
| **Failure modes** | ✅ / ⚠️ / N/A | … |
| **On-call / runbook** | ✅ / ⚠️ / N/A | … |
```

`✅` = addressed in the doc. `⚠️` = identified concern, mitigation TBD. `N/A` = does not apply (with reason).

### What each item covers

- **Security.** Auth model. Authorization. Threat surface. Tool authorization gates for state-changing actions. Prompt injection (if LLM). Input validation.
- **Privacy / PII.** What PII flows where. What's logged, what isn't. Data residency requirements. Compliance flags (GDPR, HIPAA, etc.).
- **Observability.** Logs (structured? scrubbed? retention?). Metrics. Traces. Dashboards. Alerts. Audit log for state-changing tool calls.
- **Rollout / Rollback.** Feature flag? Kill switch? Phased % rollout? Forward-compat / backward-compat plan? How do we revert?
- **Scalability.** Bottlenecks at 10× current load. Stateful vs stateless. Connection pool sizes. LLM rate limits if relevant.
- **Dependencies.** What does this depend on (services, APIs, vendors)? What depends on it? How does it fail when a dep is down?
- **Failure modes.** Top 3-5 ways this can fail. Detection. User-facing behavior under failure. Recovery.
- **On-call / runbook.** Who pages? What do they do at 3am? Where's the runbook? Is the team trained?

## Heavyweight checklist: KEP-style Production Readiness Review

For heavyweight docs (~10-20 pages, org-spanning, infra-sensitive), upgrade to the full PRR questionnaire. Borrowed from Kubernetes' [KEP template](https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md). Each section answers ~3-5 specific questions; each question can be marked N/A with reason.

### A. Feature enablement and rollback
- How can this feature be enabled/disabled at runtime?
- Does enabling/disabling require a restart? A redeploy?
- Are there any tests for feature enablement/disablement?
- What happens if the feature is enabled, then disabled? Is the system back to a clean state?

### B. Rollout, upgrade, and rollback planning
- How can rollout fail? Can it impact already-running workloads?
- What signals trigger a rollback?
- Is the rollback plan tested in dev/staging?
- Are there release-time migrations needed (data, schema, config)?

### C. Monitoring requirements
- What metrics emit success/failure of this feature?
- What logs are emitted? Are they scrubbed of PII?
- What alerts are configured?
- What dashboards visualize the feature's health?

### D. Dependencies
- Does this depend on services or APIs not under our control? Which?
- What's the failure behavior when each dependency fails?
- Are there contractual SLAs we depend on?

### E. Scalability
- What scaling vector grows fastest with usage?
- What's the projected load at MVP launch, 6 months, year 1?
- Where are the bottlenecks (DB connections, LLM rate limits, memory, CPU)?
- What's the plan when we hit 80% of any quota?

### F. Troubleshooting
- How will an on-call engineer diagnose a failure at 3am?
- What's the most likely failure mode? What does it look like in the dashboards?
- Is there a runbook? Where? Who maintains it?

### G. Security and compliance
- What new attack surface does this introduce?
- What's the auth model for any new endpoints?
- Are there privileged operations? Who can perform them?
- What audit events are logged for compliance?

## Marking N/A correctly

> "N/A" is a valid answer. "We forgot to think about it" is not.

Bad N/A: "Privacy: N/A."
Good N/A: "Privacy: N/A. This is a backend-internal change; no user data flows through the new code path. PII handling continues unchanged in service X."

The N/A reason is short but specific. A reviewer should be able to challenge it — "actually, you do touch user data via the audit log" — if the reasoning is wrong.

## Common failure modes

| Failure | Fix |
|---|---|
| **Checklist silently incomplete** | Audit script enforces presence of each line |
| **All items marked N/A** | Almost always wrong — re-read the proposal looking for the concern |
| **One-word answers** | Each ✅ needs a 1-2 sentence "what we're doing about it" |
| **PRR for a 4-page doc** | Don't over-checklist a small change. PRR is for heavyweight only. |
| **No audit-log column** | If you change state on user data, audit-log behavior is mandatory |
