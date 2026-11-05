# Decisions

2026-11-04 — Create a separate ClickOnce project; leave the prior OSWorld project and workload stopped.

2026-11-04 — Test-first implementation. No implementation exists at M0; contract tests intentionally fail until modules are built.

2026-11-04 — Train a lightweight finite-memory control policy first. This is a documented baseline, not a substitute claim for VLM RL. Frozen VLM perception and VLM adapter training have separate gates.

2026-11-04 — Use simulated action ticks, fixed fault on the first submission and honest history to keep ambiguous outcomes discoverable and reproducible. Test generalization to longer delays separately.

2026-11-04 — Use deterministic backend evaluation; do not use a VLM judge as ground truth. Keep deliberately weak UI-proxy reward for the experimental arm.

2026-11-04 — No positive intermediate rewards initially. Compare terminal rewards with identical step costs; this avoids introducing reward shaping before the core environment is validated.

2026-11-04 — Added independent record-level evaluation tests after reviewing the first experiment. Experiment-v1 used the environment's outcome label directly; it is retained as a prototype. Experiment-v2 uses a separate evaluator that ignores reward success/count fields and checks private record identity and status. Same frozen training configurations and manifests; no hyperparameter changes. Rerun is a correctness repair, not test-set tuning.

2026-11-04 — Vision-v1 stopped early after repeated empty/truncated outputs. One diagnostic with a 512-token cap produced a valid answer and exposed a thinking field despite think=false. The original 160-token budget was consumed by reasoning. Raise the cap to 1024, retain malformed responses and record generated-token/reasoning metadata. Vision-v2 is a fresh gate with identical fixtures and unchanged accuracy criteria; no model training.

2026-11-04 — Final CPU study: 120000 training episodes, 473212 transitions, 12 trained checkpoints. Strict-memory test success 100/100/100%; strict-memoryless 100/100/40%; both proxy arms 40/40/40%. Scripted verification also 100%; no RL superiority claim. All results and unstable seeds retained.

2026-11-04 — Frozen Qwen screenshot gate: 20/20 correct, 20 fresh requests, no retries, median 9.23 s, maximum 23.55 s. The model emitted reasoning despite think=false; this is included in latency. Actual screenshot-controlled pending-timeout demo passed in six actions with one submission, four fresh perceptions and two cache hits. Model unloaded afterward. No VLM weight training.

2026-11-04 — User requested stronger evaluation after the V1 ceiling. Preserve V1 unchanged as a warm-up. Add V2 protocol before experiments; use new train/validation/test seed ranges and no post-test hyperparameter changes. Do not target an arbitrary failure percentage. Report all seed outcomes and retain scripted solvability baseline. V2 diagnostic replay parameters (2 failures, 2 distractors, 3-tick history lag, pending commit delay 4) illustrate the stale-retry mechanism; not selected from locked test scores.

2026-11-05 — Evaluation audit: V2's 200 nominal test worlds collapse to 56 control configurations, 51 already represented in training. Preserve old results but remove them as headline evidence. Freeze a disjoint finite control grid with ten training seeds and matched transition budgets. Replay all saved trajectories through an independent interpreter. Add an explicitly post-hoc action-age control to expose the memory-capacity confound; do not call it preregistered.

2026-11-05 — User requested five genuinely different browser task families. Preserve booking; add a 24-game math site, real Wikipedia hyperlink navigation, source-to-email drafting and constrained vendor comparison. Thirty authored cases have independent artifact predicates and privileged solvability checks. Four app families are local synthetic sites; Wikipedia is live. Use isolated benchmark browser profiles and draft-only local mail for repeatability. No Gmail credential use or real email sending.

2026-11-05 — Local deployment development checks: existing qwen3-vl:2b is a Thinking renderer. Both it and full-resolution Instruct timed out before action generation. Smaller images (max 768 px), 3072-token context and prompt batch 64 produced timely Instruct responses. Optional action-coordinate fields were omitted on the separate development fixture; require every generation field with empty defaults for unused arguments. All deployment changes precede the 30-case frozen evaluation. No scored task was used for adapter tuning.

2026-11-05 — Resource-monitor bug found during development: a sysctl timeout killed the monitor thread. Add timeout/error handling and stop the workload if pressure cannot be measured. Tests cover unavailable monitoring and consecutive critical samples. Preserve both failed infrastructure checks rather than treating them as task failures.
