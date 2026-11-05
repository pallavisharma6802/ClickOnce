# ClickOnce: ambiguous outcomes and reward exploitation

A controlled local browser environment and CPU RL study. All bookings are synthetic. This is not an OSWorld result or a claim of a novel algorithm.

## Experiment

120,000 training episodes, 473,212 environment steps, three seeds (11/22/33), two reward designs, and memory/no-memory ablations. Each frozen policy sees the same 200 held-out test worlds. Validation and test seeds are disjoint from training. Stress evaluation reuses test identities with pending delays increased to 6–8 ticks. No post-test hyperparameter selection.

CPU experiment wall time: 11.32 seconds, excluding browser replays, VLM inference and plotting. The tabular policy receives structured public UI observations. It does not learn from pixels.

## Held-out outcomes

| Policy | Strict success | Individual training seeds | Duplicate episodes | Proxy-positive / true failure | Mean actions |
|---|---:|---|---:|---:|---:|
| Outcome reward, no memory | 80.0% | 11: 100%, 22: 100%, 33: 40% | 20.0% | 0.0% | 5.72 |
| UI reward, no memory | 40.0% | 11: 40%, 22: 40%, 33: 40% | 40.0% | 60.0% | 2.60 |
| Outcome reward + memory | 100.0% | 11: 100%, 22: 100%, 33: 100% | 0.0% | 0.0% | 4.46 |
| UI reward + memory | 40.0% | 11: 40%, 22: 40%, 33: 40% | 40.0% | 60.0% | 2.60 |
| Random baseline | 20.5% | random: 20% | 17.0% | 18.5% | 3.83 |
| Retry / trust success baseline | 40.0% | naive: 40% | 40.0% | 60.0% | 2.60 |
| Scripted verification (not learned) | 100.0% | verify: 100% | 0.0% | 0.0% | 4.19 |
| Untrained Q policy | 0.0% | untrained: 0% | 100.0% | 0.0% | 12.00 |

## What this supports

- On this small environment, outcome reward with finite action memory learned successful behavior across all three runs. UI-proxy training produced fast behavior that accepted false success or created duplicates. This is operational proxy exploitation, not evidence of deliberate cheating.
- The scripted verification baseline also succeeds. Learned behavior is not superior to a hand-coded solution here; the result is about reward design and learning stability.
- Memoryless training is unstable: seeds 11 and 22 succeed, while seed 33 succeeds only on committed/pending timeouts and fails the other three scenarios. Do not hide this behind the mean.
- Observation aliasing is verified at both JSON and screenshot levels: failed, committed and pending submissions display the same timeout before inspection.
- Strict evaluation is recomputed independently from private record identity/status. It ignores the environment reward flag and reported count fields.

## Visual model gate

{
  "model": "qwen3-vl:2b",
  "accuracy": 1.0,
  "passed": true,
  "samples": 20,
  "trained": false,
  "observation": "actual browser screenshots",
  "note": "Small engineering smoke set, not a general perception benchmark"
}

The optional visual bridge uses the installed frozen Qwen3-VL 2B model. It extracts visible status/page/row counts from actual browser screenshots. Neither VLM weights nor a VLM adapter were trained. Its 20-frame check is a small engineering smoke set; labels were visually reviewed but are not an independent large benchmark.

The recorded screenshot-driven pending-timeout episode completed in six actions: one submission, four history checks, and Finish. The evaluator found one confirmed booking and no duplicates. It used four fresh VLM calls and two cached observations; this is one smoke episode, not a visual-agent success-rate estimate.

## Limitations

- One synthetic booking application, four bounded actions, five fault types. The first submission alone is faulty; later submissions succeed. This makes the task substantially easier than real web interaction.
- Task identities differ across splits, but the learned state abstraction ignores identity and layout. Held-out success measures control under new seeds/delays, not semantic or visual generalization.
- The memory policy adds previous-action and observed-pending indicators. No recurrent neural network, full VLM RL or large model training is claimed.
- The weak proxy is deliberately misspecified. The observed exploitation gap cannot estimate its frequency in deployed agents.
- Action-driven simulation removes wall-clock races. Stress tests change delays, not the task family. UI layout robustness remains unmeasured.
- Reward arms have equal episode budgets, not equal transition counts; both counts are retained. A transition-matched study is future work.
- Three training seeds and a balanced 200-instance synthetic test suite support a bounded demonstration, not broad statistical claims. Per-seed values are reported instead of an inflated significance claim.
- The evaluator boundary is a software interface, not a hardened security sandbox. Browser routes exclude private data, but trusted in-process experiment code can access it.

## Reproduce

See README.md for installation, full tests, training, live browser and replay commands. Primary results are in runs/experiment-v2; experiment-v1 and vision-v1 are retained as development attempts. See docs/DECISIONS.md for corrections.
