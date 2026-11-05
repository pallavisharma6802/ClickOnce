# Evaluation repair v3 — frozen before the new run

Date: 2026-11-05. V1/V2 remain historical exploratory studies, not the main evidence.

## What was inadequate

The V2 500 training worlds contain 72 distinct control configurations; 200 test worlds contain 56, of which 51 were already in training. A control configuration is (failure count, history lag, pending status, effective delay), with delay ignored when there is no pending operation. Request IDs and unrelated rows do not create new control problems for the engineered policy.

The three target-only checkpoints have different hashes. Their 200-element outcome vectors are identical, but seed 22 differs from seed 11 in action counts on 146 cases, and seed 33 differs on 64. Equal scores were genuine repeated behavior, not evidence of three independent task populations. Three seeds and a narrow familiar-generator test were insufficient for a generalization claim. The old percentages must be labeled exploratory.

## Study population and limits

One booking-task family, four bounded semantic actions. Do not call scenario cells distinct applications or task families. No VLM training or visual-generalization claim.

Enumerate the control grid instead of sampling duplicate cases:
- Training/domain-validation: failure count 0..3 and history lag 0..3, but never both nonzero; pending=False (effective delay 0) or pending=True with delay 2..5. Seven failure/lag pairs times five completion settings = 35 cells.
- Composition holdout: failures 1..3 AND lag 1..3, with the same five completion settings = 45 cells. Parameter values are individually familiar; their combination never occurs in training.
- Timing extrapolation: every failure/lag pair, pending=True, delay 6..10 = 80 cells. These delays never occur in training or composition evaluation.
- Every cell uses one unrelated original booking. Presentation/request seeds are separate and are not counted as extra independent cases.
- A 40-action cap is identical across training and all evaluation partitions. A public-only reference must solve every cell at this cap before learning results are interpreted. No cases are removed after seeing learned-agent outcomes.

These are finite-grid censuses, not samples of all websites. Report exact per-cell results; do not manufacture a confidence interval by resampling renamed copies of cells.

## Training and selection

Ten independent training seeds, 101..110, for each of two fixed arms: target matching without freshness; target matching with visible freshness. Both use the existing EvidenceLearner, alpha=.15, gamma=.95, and 100000 environment transitions per seed, not unequal episode budgets. Same training cell stream and exploration RNG stream for each paired seed. Any differences caused by actions remain part of learning. Exploration decreases linearly from .8 to .04 over the first 85000 transitions. One CPU process, no VLM or GPU.

Record snapshots at 20000, 50000, 100000 transitions. Choose the last checkpoint by rule; do not choose the best checkpoint. Domain-validation uses only training control cells with new presentation seeds and does not tune parameters. Composition and timing results are produced only after all models are frozen. Retain every seed and all failures.

Baselines: random, retry/trust-success, target-only scripted, freshness-aware scripted, and frozen V2 checkpoints. Treat the scripted baselines as mechanistic controls, not learned achievements. No claim of beating the scripted reference.

## Verification

An independently written reference transition interpreter (no calls to ClickOnceEnv or its audit/evaluation functions) recomputes request commits, pending transitions, snapshot rows, deadlines, rewards and strict outcomes. Compare every observation and reward on every evaluated action, not merely the final label. A deliberately altered reward or history row must fail the checker. Backend-audit outcome labels are never policy inputs.

Persist immutable protocol/source/checkpoint hashes, manifests, per-episode records, errors and action traces. Do not silently drop invalid outputs or evaluator failures. An infrastructure exception makes the evaluation fail loudly, rather than becoming a task success/failure observation.

## Statistics

Report success, duplicate side effects, false completion, truncation, action count and checks separately for each partition and training seed. Report macro-averages over equally weighted unique cells, not presentation variants. Across the ten training seeds, show mean, standard deviation, min/max and a percentile bootstrap interval for the mean (10000 resamples, fixed bootstrap seed 901). That interval measures training-seed uncertainty conditional on this finite grid; it is not a confidence interval for real-world computer use.

For the ablation, pair seeds and cells, then report the per-seed difference and its bootstrap interval. Publish paired win/loss/tie counts and failure-cell IDs. Publish behavior fingerprints to expose collapsed/deterministic policies. Equal scores are allowed and explained; never add noise or pick seeds to make tables look varied.

## Next task-suite expansion

A stronger portfolio claim still needs genuinely different workflows (e.g. creating a record, editing an existing record with a version conflict, cancelling an operation, and draft/confirm workflows). Renaming Book to Send does not count. Build these with separate task-state graphs and independently tested success predicates, then hold out a workflow family and UI template. This evaluation repair cannot substitute for that future environment work.
