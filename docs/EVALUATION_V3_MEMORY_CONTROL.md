# Post-hoc memory control — 2026-11-05

The preregistered two-arm census saturated the freshness-aware policy. A causal claim that freshness information is necessary would be unjustified: the no-freshness policy has only one-action memory and cannot explicitly count elapsed steps. This is a representation-capacity confound, not just a task-count issue.

Add a secondary control, openly marked post hoc: a no-freshness policy with an action-age counter (0..12), trained for the same 100000 transitions for each seed 101..110, using only the same 35 domain cells. Keep alpha, gamma, exploration, test partitions and all other features unchanged. It cannot read current tick, snapshot tick or submission timestamp from history_meta; the counter uses its own actions only. No configuration is selected from holdout scores.

Also evaluate a public-only conservative scripted verifier that never reads freshness metadata and waits until its own action count reaches the known maximum history lag before treating an empty snapshot as failed. This determines whether freshness is necessary for safe completion or merely improves efficiency. The maximum lag is an environment-contract assumption, not the hidden lag for a specific episode. Report that assumption.

These controls are exploratory additions after seeing the primary results; their intervals are descriptive, not a preregistered confirmation. They test an alternative explanation. Do not replace the original failed seeds, rerun the original arms, or silently rewrite the frozen protocol. Original source files are archived and verified against the original source hashes.
