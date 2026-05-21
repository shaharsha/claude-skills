# Gemini (Google) — Provider Deep-Dive

Applies to the **Gemini model family** wherever it runs: the Gemini API (Google AI Studio) and Vertex AI. The platform does not change prompt engineering — the model version does.

**Current models (May 2026):** Gemini 3.5 Flash (`gemini-3.5-flash`, released May 19 2026) is a fast, low-cost frontier model with strong agentic and multimodal performance; Gemini 3.1 Pro is the most capable reasoning model; Gemini 3 Pro/Flash and Gemini 2.5 remain in use. Gemini 3.x models are tuned for advanced reasoning and instruction following and respond best to prompts that are direct, well-structured, and explicit about the task and constraints.

## Contents
- System instructions and placement
- Sampling parameters (don't set them)
- Thinking level
- Thought preservation and signatures
- Few-shot examples
- Completion priming
- Verbosity
- Grounding and built-in tools
- Function calling
- Tool-use control and error recovery
- Non-English output
- Temporal grounding
- Multimodal
- Flash tier
- Migration to Gemini 3.5

## System instructions and placement

Use `system_instruction` for role, behavioral rules, and format requirements. Gemini has a **recency bias** — put the most critical constraints **last**, and for large inputs put long context first and the actual query at the end, bridged with a phrase like "Based on the above...". Use one structural convention consistently (XML tags or markdown headings — don't mix).

## Sampling parameters (don't set them)

For Gemini 3.x, **do not set `temperature`, `top_p`, or `top_k`** — Google strongly recommends leaving them at default. The models are optimized for default sampling and custom values can degrade reasoning. For determinism, use explicit rules in the system instruction and structured outputs (`responseSchema`), not sampling tweaks. (On older Gemini 2.5 a default of 1.0 was the guidance; on 3.x, omit the parameters entirely.)

## Thinking level

Gemini 3.x uses `thinking_level` (`minimal` / `low` / `medium` / `high`), replacing the older numeric `thinking_budget`. Default is `medium` (Gemini 3.5 Flash). Start at `medium`; drop to `low` for faster responses; escalate to `high` only for hard reasoning, math, or difficult coding. If an older prompt used chain-of-thought text to force reasoning, delete that scaffolding and raise `thinking_level` with a simpler prompt instead.

## Thought preservation and signatures

On Gemini 3.5, **thought preservation is on by default** — the model carries intermediate reasoning across multi-turn conversations automatically, which improves iterative tasks (debugging, refactoring) but can increase token usage. With the GenerateContent API this works as long as **thought signatures** stay in the conversation history: capture the `thoughtSignature` returned with function calls and pass it back with results to keep the reasoning chain coherent.

## Few-shot examples

Few-shot examples are **critical** on Gemini — "prompts without few-shot examples are likely to be less effective." Include several diverse input/output examples with clear `INPUT:` / `OUTPUT:` labels. Keep formatting, spacing, tags, and delimiters identical across every example — inconsistency confuses the model. Use enough examples to establish the pattern but not so many that responses overfit to the samples.

## Completion priming

Gemini responds more reliably to **completion priming** than to described format preferences — start the response (an outline's first line, the opening of a JSON structure) and let the model continue the pattern, rather than only describing the desired shape.

## Verbosity

Gemini 3.x defaults to **terse, efficient answers**. If you want a detailed or conversational response, request it explicitly in the instructions — the model will not elaborate on its own.

## Grounding and built-in tools

Gemini has native **Google Search grounding** — the exclusive anti-hallucination tool, connecting the model to real-time verified information. Enable it for current or obscure facts; enable code execution for calculations. Gemini 3 can combine built-in tools (Search, URL context, code execution) with custom function calling in a single request.

## Function calling

- Each function response must include the `id`, a matching `name`, and exactly one response per call.
- Place multimodal content (images, audio) **inside** function-response parts, not alongside them.
- Append extra runtime guidance to the function-response text (separated by two newlines), not as a separate part.

## Tool-use control and error recovery

If the model overuses tools, first lower `thinking_level`, then add a system instruction constraining the usage budget. Gemini benefits from an explicit error-recovery rule: **"Don't repeat a failed call with identical arguments"** — change the query, parameters, or approach on retry.

## Non-English output

Gemini needs **aggressive** language enforcement to hold a non-English output language — a mild instruction drifts. Use emphatic, explicit wording: "RESPOND IN {LANGUAGE}. YOU MUST RESPOND UNMISTAKABLY IN {LANGUAGE}."

## Temporal grounding

For time-sensitive tasks, anchor the date explicitly: "Remember it is {YEAR} this year." Gemini benefits from being told the current date even though it can ground via Search.

## Multimodal

Treat text, images, audio, and video as equal-class inputs and reference each clearly in the instruction with explicit labels. Test the `media_resolution` setting for PDFs and dense documents — higher resolution improves fidelity but increases token usage. Image segmentation is unsupported on Gemini 3.x (use Gemini 2.5 Flash or Robotics-ER); Computer Use is not yet supported on Gemini 3.5 Flash (use Gemini 3 Flash Preview).

## Flash tier

Gemini 3.5 Flash / 3 Flash / Flash Lite are the budget tier — excellent for classification, routing, and high-volume multimodal batch work; Flash Lite is the best value for high-volume batch. Give Flash-tier models more explicit instructions and more (simpler) few-shot examples than you would a Pro model, and keep the tool set small and clearly bounded.

## Migration to Gemini 3.5

- Update the model ID to `gemini-3.5-flash` (or the relevant 3.x model).
- Remove `temperature`, `top_p`, `top_k` from the request config.
- Replace `thinking_budget` (numeric) with `thinking_level` (`minimal`/`low`/`medium`/`high`).
- Delete chain-of-thought scaffolding that forced reasoning — use `thinking_level` instead.
- Expect thought preservation on by default; ensure thought signatures round-trip with function results.
- Re-test: Gemini 3.x is terser and more direct — prompts written for a chattier older model may need an explicit elaboration request.
