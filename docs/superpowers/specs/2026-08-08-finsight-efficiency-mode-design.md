# Finsight Efficiency Mode Design

## Goal

Create a Finsight-only Codex skill that preserves analytical quality while limiting unnecessary context, model, and subagent usage.

## Delegation policy

- Sol remains the orchestrator and makes the delegation decision.
- Sol delegates only when a bounded subtask can materially improve the result.
- Default maximum: two concurrent subagents. More requires an explicit justification in the working thread.
- Routine evidence-gathering uses `gpt-5.6-terra` with medium reasoning.
- Complex or high-risk specialist work uses `gpt-5.6-luna` with high reasoning.
- Sol synthesizes all outputs and performs the final consistency check.
- Existing agents are not silently converted to another model; replacement requires explicit closure and redeployment.

## Efficiency controls

- Give each agent a disjoint, narrow scope.
- Pass file paths, targeted Graphify/Obsidian notes, and concise summaries instead of broad vault or repository dumps.
- Do not ask multiple agents to repeat the same search or review.
- Prefer one agent or Sol alone for simple tasks.
- Close completed agents when the platform exposes agent lifecycle controls.
- Do not use OpenAI API calls, external paid model calls, or network retrieval for this workflow unless the user explicitly requests it.

## Quality controls

- Every delegated task must state its deliverable and evidence standard.
- Agents should return concise findings with file paths, line references, test results, or calculation traces where applicable.
- Sol must identify uncertainty, reconcile disagreements, and verify important claims before presenting a conclusion.
- For valuation work, separate mechanical checks from judgment-heavy assumptions and route the latter to Luna High when warranted.

## Skill shape

Use a project-local skill with one compact reference file:

- `.agents/skills/finsight-efficiency/SKILL.md`: trigger, routing workflow, delegation templates, and final synthesis rules.
- `.agents/skills/finsight-efficiency/references/finsight-context.md`: concise Finsight domains, important paths, and Graphify/Obsidian context-loading rules.

No hooks, scripts, API clients, or automatic background agents are required. The skill is activated explicitly by mentioning `finsight-efficiency` or “Finsight Efficiency Mode.”
