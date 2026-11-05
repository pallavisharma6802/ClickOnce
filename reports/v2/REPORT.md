# ClickOnce V2: why the first benchmark was too easy

The V1 result is retained as a unit-scale learnability demonstration. V2 adds repeated failures, unrelated bookings and visibly stale history. No target failure percentage was used. Configurations were frozen before new test evaluation.

## Held-out outcomes

| Policy | Overall | Clean | Repeated faults | Distractors | Stale history | Combined |
|---|---:|---:|---:|---:|---:|---:|
| target_only_11 | 71.5% | 100.0% | 100.0% | 100.0% | 30.0% | 27.5% |
| target_only_22 | 71.5% | 100.0% | 100.0% | 100.0% | 30.0% | 27.5% |
| target_only_33 | 71.5% | 100.0% | 100.0% | 100.0% | 30.0% | 27.5% |
| freshness_11 | 86.0% | 82.5% | 80.0% | 80.0% | 92.5% | 95.0% |
| freshness_22 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| freshness_33 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| v1_learned | 46.0% | 100.0% | 100.0% | 0.0% | 30.0% | 0.0% |
| v1_rule | 66.0% | 100.0% | 100.0% | 100.0% | 30.0% | 0.0% |
| target_rule | 71.5% | 100.0% | 100.0% | 100.0% | 30.0% | 27.5% |
| fresh_rule | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## Interpretation

The frozen V1 learned policy transfers at 46.0%, down from 100% on V1. That is an environment/representation limitation, not a regression in the preserved checkpoint.
Target-aware RL without freshness: mean 71.5%; seeds 71.5%, 71.5%, 71.5%.
Freshness-aware RL: mean 95.3%; seeds 86.0%, 100.0%, 100.0%. Seed 11 remains imperfect; it is not replaced by the best seed.
The difference is an ablation of engineered visible freshness features under the same training budget; it is not proof of a new architecture or general visual reasoning.
The freshness-aware scripted baseline is still 100%. The environment has a valid, publicly observable solution. The study identifies missing evidence handling, not superiority over scripting.

## Protocol and limits

Three seeds, 10000 training episodes per arm, 200 paired test cases (40 per tier). New disjoint seed ranges; train/validation/test all sample the specified tier generator. New seeds are not held-out app templates or composition-OOD generalization.
V2 still uses bounded semantic actions and engineered target equality/freshness features. No V2 VLM training or pixel-control result is claimed. The frozen visual-model smoke test in V1 does not establish V2 perception accuracy.
Training reward is outcome-based in both ablation arms. Raw counts, private audits, checkpoints and validation results are preserved. Wrong-target additions and alteration/removal of unrelated initial records fail independent evaluation.

## Reproduce

`uv run python -m click_once.hardening --output runs/new-v2 --episodes 10000`
`uv run --extra report python scripts/report_v2.py`

See docs/V2_PROTOCOL.md for the frozen design.