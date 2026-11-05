# Completion status — 2026-11-04

M0: plan and test contracts complete; original red baseline retained.
M1: all five scenarios, private state, public projection, independent record-level evaluator and Gymnasium adapter implemented and tested.
M2: actual Chrome UI, action execution, pixel-identical ambiguous screens, reload persistence and private-route exclusion tested.
M3: CPU Q-learning experiment complete: 12 checkpoints, 3 seeds per arm, 120000 training episodes, 473212 transitions, validation/test/stress evaluation. All 3200 held-out outcome records independently rechecked.
M4: frozen local Qwen gate passed 20/20 actual screenshots. A six-action screenshot-driven browser episode passed with zero duplicate bookings. No VLM weights were trained.
M5: report, figures, interactive replay dashboard, raw artifacts, dependency lock, fresh installation check and one-command reproduction included.

Verification: 57 tests passed with real browser tests enabled, no skips. Dashboard JavaScript, split selector, replay slider and screenshot assets validated in Chrome and screenshot reviewed. No critical memory stop. Ollama model unloaded and task-owned browsers/servers closed.

Research limits: one synthetic booking app; four semantic GUI actions; tabular policy learns on structured public state. Frozen VLM bridges screenshots only at inference. A scripted verification policy also solves every scenario. Full VLM RL, arbitrary coordinate grounding, varied app families and layout-generalization evaluation are not part of this release.

## V2 hardening — 2026-11-04

Added repeated faults, unrelated initial records, stale-history snapshots with browser-visible freshness timestamps, and an independent collateral-preservation check. Six additional policies trained on new splits with freshness/no-freshness ablation. Frozen V1 transfer is 46%; freshness-aware learned seeds score 86/100/100%; no-freshness learned seeds score 71.5/71.5/71.5%. The scripted reference remains 100%. All 2000 held-out policy/case outcomes were checked against private records. 71 tests pass with actual browser tests enabled.

V2 replay is an illustrative controlled diagnostic at a fixed validation-range seed and explicit compound parameters, not evidence for an aggregate rate. V2 uses structured observations only; the old frozen VLM smoke does not establish V2 visual accuracy.
