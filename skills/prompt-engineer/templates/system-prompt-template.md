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
- **Examples** are the most reliable steering mechanism. Include 3-5, covering edge cases.
- **Put long reference documents ABOVE this template** in the actual prompt, instructions at the bottom.
- **Start minimal.** Add sections only when you observe failure modes that need addressing.
