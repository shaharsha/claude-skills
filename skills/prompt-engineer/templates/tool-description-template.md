# Tool Description Template

Every tool description must cover these elements. Count coverage across the description, the parameter descriptions, enums and the tool's errors, not sentences: Anthropic asks for at least 3-4 sentences per description (more for complex tools), and budget models need more spelled out (5-6).

---

## Template

```
[What it does — one clear sentence describing the tool's purpose.]

[When to use it — specific triggers, conditions, or user intents that warrant this tool.]

[When NOT to use it — common misuse cases, overlapping tools to prefer instead, or scenarios where this tool is the wrong choice.]

Parameters:
    param_name: [Type]. [What it means, valid values/format, constraints].
        Example: "AAPL", "2024-01-15"
    optional_param: [Type, optional]. [What it does when provided vs. omitted].
        Default: [default value]

Returns:
    [What the response contains — be specific about fields/structure.]
    [What it does NOT return — to prevent hallucinated assumptions.]

[Caveats/limitations — rate limits, data freshness, error conditions, etc.]

[Cost or latency, if notable. Fails when X; then do Y. Retry: transient (once, and only if repeating is safe: read-only, idempotent, or checked first) / fix the input / never (a denial).]
[Async tools only: how completion arrives. If the harness notifies, say there is no need to poll; if not, name the status call and how often to check.]
```

---

## Worked Example

```
Search for projects in the database using full-text search.

Use when the user asks about specific projects, past work, or experience
in a particular domain. Supports prefix matching for non-Latin scripts.
Do NOT use for searching employees or clients — use search_employees
or search_clients instead.

Parameters:
    query: str. Search terms. For prefix matching, use at least
        2 characters. Example: "audit municipal"
    limit: int, optional. Max results to return. Default 10. Use higher
        values only when comprehensive coverage is needed.

Returns:
    List of records with: project_id, name, client_name, year, scope,
    team_members. Does NOT include financial data — use
    get_project_details for billing information.
```

Why this works: covers all 6 elements (what/when/when-not/params/returns/caveats), names the alternative tools explicitly, shows parameter examples, and states what is NOT returned to prevent hallucinated assumptions.

---

## Checklist

- [ ] First sentence clearly states what the tool does
- [ ] "When to use" includes specific triggers (not just "when relevant")
- [ ] "When NOT to use" prevents common misuse and names alternatives
- [ ] Every parameter has type, meaning, and constraints
- [ ] Return value is specific about what's included AND excluded
- [ ] The six elements are covered across the description and schema (Anthropic: at least 3-4 description sentences; no padding; trim hand-holding on frontier models)
- [ ] Failures are covered: what the tool fails on, the next step, and whether a retry can help
- [ ] Fields a person reads (a command's summary, an approval reason) state a length and show an example
- [ ] Anything the UI adds itself (for example an "Other" option on a question) is named, so the model doesn't add it twice
- [ ] Parameters that multiply cost (model, effort, fan-out) are used only when the user asked for them
- [ ] The model isn't asked to fill arguments your code already knows (pass them in code instead)
- [ ] Invalid combinations are impossible by schema (enums, required fields), not just forbidden in prose
- [ ] Each piece of guidance is stated once: here, or (on GPT) the routing between tools in the system prompt, as OpenAI's function-calling guide places it
- [ ] If the tool must be called (Claude Opus 5.5 / Sonnet 5.5 / Fable 5.1 / 5.2 have no forced `tool_choice`), the prompt says when it applies
