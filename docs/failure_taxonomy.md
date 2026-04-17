# Failure Taxonomy for Qwen3.6 OSWorld Qualitative Analysis

Tags are agent-suggested unless a human later marks them verified.

## Primary model-failure tags

### `visual_perception`
Use when the model appears to misread, miss, or hallucinate visible UI evidence.
Examples:
- Misses a visible button/icon/text label.
- Treats a disabled/inactive control as active.
- Misreads selected state, dialog contents, or layout.

### `action_grounding`
Use when the high-level intent is plausible but the action is grounded to the wrong target.
Examples:
- Clicks near but not on the intended element.
- Uses an incorrect coordinate system or spatial reference.
- Types into the wrong field after identifying the right goal.

### `planning`
Use when the next subgoal/decomposition is wrong independent of obvious perception/grounding failure.
Examples:
- Repeats an ineffective action loop.
- Stops before completing the task.
- Pursues a wrong workflow even while UI evidence is clear.

### `tool_ui_confusion`
Use when the model misunderstands OS/app interaction conventions.
Examples:
- Confuses browser tabs, app windows, menus, context dialogs, or file pickers.
- Misunderstands available actions or modal state.
- Uses the wrong application/tool for the task.

## Non-primary categories

### `mixed_uncertain`
Use when no single primary cause dominates or the trajectory is too ambiguous.

### `environment_invalid`
Not a model-failure tag. Use status `environment_invalid` when setup/provider/network/VM/recording/evaluator issues prevent fair attribution.

### `unknown`
Not counted as model failure or environment failure. Use only until enough evidence exists to classify.

## Reporting rules
- Every representative case must link to task ID, trajectory index row, screenshots/observations, raw model output, and action sequence when available.
- If a primary category is absent in the sample, the report must say `not observed in this sample`.
- Do not treat the sampled qualitative counts as a full OSWorld leaderboard result.
