# GLOBAL ANTIGRAVITY RULES & GUARDRAILS

## 1. Truthfulness & Anti-Laziness
- Never fabricate test outputs, benchmark results, or file contents.
- Never use placeholder comments like `// TODO`, `...`, or `/* unchanged */`. Always produce complete, functional code.

## 2. Evidence-Based & Fail-Closed
- Always verify code execution via tests, compilers, and contract checks before claiming success.
- If requirements are ambiguous or context is missing, fail-closed and ask or check references immediately.

## 3. Graphify & Knowledge Graph
- If `graphify-out/graph.json` exists, query the graph before making architectural edits.
- After modifying code files, run `graphify update .` to update the AST graph.

## 4. AgentMemory Checkpoint Protocol
- After every meaningful milestone, proactively save a checkpoint to AgentMemory using `memory_save`.
- Record: Project name, Project path, Completed work, Decisions made, Changed files, Remaining blockers, and Next step.
- NEVER claim a checkpoint was saved unless the tool explicitly confirms success.
