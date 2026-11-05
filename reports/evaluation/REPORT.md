# Evaluation audit and repair

## What was wrong with the old evaluation

The old 200 test worlds contained only 56 distinct control configurations; 51 were represented in training. Request IDs were not new problems for this policy. The repeated 71.5% values were not fabricated: model files differ, action counts differ, but the same cases pass/fail. The old tables were inadequate evidence of generalization.

The actual learned component is a small tabular policy. Those percentages were never Qwen solving real web tasks. The new five-family browser suite is a separate evaluation.

## Repaired protocol

Ten training seeds per arm, 100000 transitions each, fixed final checkpoint, 40 actions per episode. The primary two-arm study uses 2 million transitions. An explicitly post-hoc action-age-memory control adds 1 million transitions; no original seed is replaced.

Unique control-cell census: 35 familiar-domain cells, 45 unseen combinations of individually familiar failure/lag values, and 80 unfamiliar-delay cells. No renamed copies are counted as independent tasks. Training/composition/timing control keys are disjoint. This is still one task family.

## Results

| Partition | Policy | Mean success | Empirical 95% seed-bootstrap interval | Min–max across seeds |
|---|---|---:|---:|---:|
| domain | Target-only, one-step memory | 68.6% | 50.0%–81.4% | 0.0%–85.7% |
| domain | Visible freshness, one-step memory | 100.0% | 100.0%–100.0% | 100.0%–100.0% |
| domain | Own action-age memory, no freshness (post hoc) | 98.6% | 95.7%–100.0% | 85.7%–100.0% |
| composition | Target-only, one-step memory | 45.3% | 30.7%–58.7% | 0.0%–66.7% |
| composition | Visible freshness, one-step memory | 100.0% | 100.0%–100.0% | 100.0%–100.0% |
| composition | Own action-age memory, no freshness (post hoc) | 99.3% | 98.0%–100.0% | 93.3%–100.0% |
| timing | Target-only, one-step memory | 45.0% | 25.0%–62.5% | 0.0%–75.0% |
| timing | Visible freshness, one-step memory | 100.0% | 100.0%–100.0% | 100.0%–100.0% |
| timing | Own action-age memory, no freshness (post hoc) | 4.5% | 0.0%–10.5% | 0.0%–30.0% |

## Interpretation and alternative explanations

Additional action-count memory recovers nearly all composition performance without reading freshness. Therefore the old freshness-versus-no-freshness comparison partly confounded information with memory capacity.
The action-age control fails on unfamiliar delays. Independent replay found zero episodes visiting absent frozen Q-table keys in all three learned arms. Missing-key fallback therefore does not explain these failures. State aliasing and poorly learned values are possible explanations that have not been isolated; these are not VLM reasoning results.
The timestamp-free conservative scripted reference solves every cell by using the publicly specified maximum cache lag. Freshness metadata is not necessary for safe completion in this environment; it can reduce waiting/checking and simplify the learned state representation.
The freshness-aware policy remains perfect across these ten training seeds. We do not lower or perturb the score to make the project look harder. This is a ceiling for a small engineered-state problem. It is not evidence of general computer use.

The bootstrap intervals describe training-seed uncertainty conditional on this finite grid, not uncertainty across real websites. A degenerate 100%–100% bootstrap interval does not prove zero risk: even 10/10 perfect independent seed trials give only a 69.2% two-sided exact 95% lower bound on the probability of a perfect seed.

All 5920 saved episodes were replayed through an independently implemented transition interpreter: every observation, reward and terminal outcome was checked. Mutation tests deliberately corrupt rewards/history and verify rejection. Hashes verify frozen checkpoints.

## Every seed, not three rounded copies

| Partition / arm | Seeds 101 through 110 | Unique outcome vectors | Unique action-sequence vectors | Episodes visiting unseen state keys |
|---|---|---:|---:|---:|
| domain / target_only | 85.7%, 85.7%, 71.4%, 71.4%, 85.7%, 0.0%, 85.7%, 85.7%, 71.4%, 42.9% | 4 | 9 | 0.0% |
| domain / freshness | 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0% | 1 | 10 | 0.0% |
| domain / elapsed | 100.0%, 85.7%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0% | 2 | 9 | 0.0% |
| composition / target_only | 66.7%, 66.7%, 33.3%, 33.3%, 66.7%, 0.0%, 66.7%, 66.7%, 33.3%, 20.0% | 4 | 9 | 0.0% |
| composition / freshness | 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0% | 1 | 10 | 0.0% |
| composition / elapsed | 100.0%, 93.3%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0% | 2 | 9 | 0.0% |
| timing / target_only | 75.0%, 0.0%, 50.0%, 50.0%, 75.0%, 0.0%, 75.0%, 75.0%, 50.0%, 0.0% | 3 | 9 | 0.0% |
| timing / freshness | 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0%, 100.0% | 1 | 10 | 0.0% |
| timing / elapsed | 0.0%, 0.0%, 0.0%, 30.0%, 0.0%, 15.0%, 0.0%, 0.0%, 0.0%, 0.0% | 3 | 7 | 0.0% |

## What a larger task suite must add

More scenario instances alone cannot supply task diversity. The separate browser suite adds math puzzles, actual Wikipedia hyperlink navigation, cross-page email drafting and constrained offer comparison. Those are actual Qwen screenshot evaluations, with separate task-specific checks. Do not pool their scores with this tabular study.

## Reproduce

```sh
uv run python -m click_once.evaluation --output runs/new-evaluation --budget 100000
uv run python -m click_once.memory_control --output runs/new-memory-control --budget 100000
```

Primary artifacts: runs/evaluation-v3. Secondary artifacts: runs/evaluation-v3-memory-control. Frozen protocols: docs/EVALUATION_V3.md and docs/EVALUATION_V3_MEMORY_CONTROL.md. Full per-case outcomes and action traces remain available.