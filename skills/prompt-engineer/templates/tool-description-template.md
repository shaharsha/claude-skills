# Tool Description Template

Every tool description must cover these elements. Minimum 3-4 sentences for full models, 5-6 for budget models.

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
- [ ] Total description is at least 3-4 sentences
