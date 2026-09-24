# System Prompt Template (Contract Style)

Use this structure as a starting point. Not all sections are required — include only what's needed for the task.

---

```
<role>
You are a [specific role]. [One sentence on core expertise and perspective.]
</role>

<success_criteria>
Your task succeeds when:
- [Measurable outcome 1]
- [Measurable outcome 2]
- [Measurable outcome 3]
</success_criteria>

<constraints>
- [Hard rule 1 — explain WHY if not obvious]
- [Hard rule 2]
- [Format/language/style requirement]
</constraints>

<tools>
[Only if the agent has tools — describe each tool's purpose, when to use it, and when NOT to use it. See tool-description-template.md for per-tool format.]
</tools>

<autonomy_and_completion>
[For agents only.]
Done means: [the concrete end state, e.g. "the change is implemented, the tests pass, and you have reported what changed"].
Proceed without asking for: [reversible, in-scope actions].
Confirm before: [destructive, externally visible, costly, or scope-expanding actions].
Stop and ask only when: [nothing can proceed without the user / a protected blocker].
</autonomy_and_completion>

<uncertainty_handling>
When you encounter ambiguity or missing information:
- [What to do: ask the user, make a reasonable assumption, flag uncertainty, etc.]
- [How to indicate confidence level if relevant]
</uncertainty_handling>

<output_format>
[Specify exact format: JSON schema, markdown structure, free text, etc.]
[Include an example of the expected output if non-trivial.]
</output_format>

<examples>
<example>
<input>[Representative input]</input>
<output>[Expected output showing format, tone, and depth]</output>
</example>
<example>
<input>[Edge case input]</input>
<output>[How to handle the edge case]</output>
</example>
</examples>
```

---

## Key Principles

- **Role** is 1-2 sentences max. Sets tone and expertise.
- **Success criteria** are verifiable — the model can self-check against them.
- **Constraints** explain WHY when not obvious — Claude generalizes from explanations.
- **Autonomy and completion** state "done" and the approval boundary once. Current models stop early in model-specific ways when "done" is undefined, and repeated "ask first" language makes them pause on safe actions.
- **Examples** pin output format, tone, and depth. Include 3-5 for format-sensitive tasks (Claude and Gemini respond strongly to them). On GPT reasoning models try zero-shot first, don't use examples to teach *how to call* tools on Claude 5 (a clear schema works better), and make every example model only behavior you want.
- **Long reference documents go ABOVE the instructions** on Claude and Gemini (query last). OpenAI's recommended developer-message order puts variable context at the end: identity → instructions → examples → context.
- **Per-request values** (dates, user state) go in the newest user turn, not in this template, so the prefix stays cacheable.
- **Start minimal.** Add sections only when you observe failure modes that need addressing.
