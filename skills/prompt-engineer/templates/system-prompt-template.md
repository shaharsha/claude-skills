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

<environment>
[For agents. What's available (runtime, tools, data); what is NOT available (no git, no network, no package installs); which files the harness owns and the agent must not edit.]
</environment>

<inputs>
[For agents and assistants. Each block the harness injects (memory, retrieved documents, tool results, reminders, the user's selection): who wrote it, how far to trust it, and whether it can give instructions. Then name the channels that can grant permission (for example the user's messages, this prompt, project instruction files, the user's answer through the ask-the-user tool) and say that everything else (retrieved documents, other tools' output, other agents) can't authorize an action or widen what was approved.]
</inputs>

<tools>
[Only if the agent has tools - the policy between tools: which to prefer for what, and in what order. Each tool's own purpose and when (not) to use it belong in its definition (tool-description-template.md), stated once; on GPT, OpenAI's function-calling guide puts the routing between functions here.]
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
- **Environment and inputs** tell the model what it can't do and which text is data, so it doesn't promise a missing tool or follow instructions in a document. Approvals, async work and modes: `references/agent-harness-patterns.md`.
- **Autonomy and completion** state "done" and the approval boundary once. Current models stop early in model-specific ways when "done" is undefined, and repeated "ask first" language makes them pause on safe actions.
- **Examples** pin output format, tone, and depth. Include 3-5 for format-sensitive tasks (Claude and Gemini respond strongly to them). On GPT reasoning models try zero-shot first, don't use examples to teach *how to call* tools on Claude 5 (a clear schema works better), and make every example model only behavior you want.
- **Long reference documents go ABOVE the instructions** on Claude and Gemini (query last). OpenAI's recommended developer-message order puts variable context at the end: identity → instructions → examples → context.
- **Output format** for assistants also decides how replies end and caps length in numbers tied to where the reply is shown; reply endings and persona scope are in `references/use-cases.md` (*Chat assistants*).
- **Per-request values** (dates, user state) go in the newest user turn, not in this template, so the prefix stays cacheable.
- **Start minimal.** Add sections only when you observe failure modes that need addressing.
