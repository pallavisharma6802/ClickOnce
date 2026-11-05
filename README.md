# ClickOnce

**A timeout is not a reason to click again.**

A local browser environment and evaluation suite for computer-use agents: booking, math puzzles, Wikipedia navigation, source-to-email drafting and vendor comparison. Independent graders check saved outcomes; agents see the interface. The original booking environment also supports lightweight tabular RL experiments.

[Read the evaluation audit](reports/evaluation/index.html) · [Historical V2 browser replays](reports/v2/index.html) · [Read the V2 report](reports/v2/REPORT.md) · [Original V1 study](reports/index.html) · [Architecture and plan](docs/PLAN.md)

## Scope

This research prototype runs on macOS **inside local Chrome**. It does not control Finder, Calendar, or other native Mac applications. Historical RL experiments train a small decision policy. The new suite uses frozen Qwen to choose browser actions from screenshots. It is not a production-ready general desktop agent or a VLM fine-tuning project.

## What actually runs

- Five browser task families, 30 authored cases, screenshot observations, mouse/keyboard actions and a Gymnasium adapter.
- The original deterministic booking simulator with seeded faults and a small action space for CPU RL.
- A real local browser interface, screenshot recording, and offline replay viewer.
- CPU tabular Q-learning, memory/no-memory ablations, two reward designs, and three independent training seeds per arm.
- A separate, record-level evaluator that ignores reward success labels and catches duplicates and incorrect task identities.
- An optional frozen **Qwen3-VL 2B** screenshot-perception adapter through local Ollama.

**Training target:** the small Q-learning policy. VLM weights were not trained. Main experiments use structured public UI observations; visual perception is evaluated separately and connected to a browser demo. This is not an OSWorld benchmark result or a general-purpose web agent.

## Evaluation audit and broader browser suite

The repeated V2 percentages came from a narrow control grid: 51 of the 56 distinct test control configurations were already represented in training. V1/V2 below are historical warm-ups, not evidence of broad computer-use skill.

The [evaluation audit](reports/evaluation/REPORT.md) uses ten training seeds, disjoint control compositions, longer-delay extrapolation and an independent transition interpreter. The counter-memory control exposes an important representation confound. These remain tabular RL experiments, not Qwen scores.

The [five-family protocol](docs/TASK_SUITE_V4.md) adds 30 authored cases: exactly-once booking, arithmetic puzzles, live Wikipedia hyperlink navigation, source-to-email drafting, and vendor comparison. Each family has easy/medium/hard variants and independent artifact checks. An actual frozen local Qwen screenshot agent receives pixels and its own memory; it cannot read DOM or hidden answers. Four task sites are local benchmark applications; Wikipedia is live. Drafts do not use Gmail or send mail.

**Execution status:** [browser report and screenshot replays](reports/browser-suite/index.html). All 30 cases passed privileged solvability checks. One completed Qwen attempt failed (24 booking submissions, 23 duplicates); the next case was interrupted. The batch was stopped as global swap grew from 10.0 GB to 18.8 GB and latency increased on the 8 GB Mac. The model is unloaded. Twenty-eight cases remain unrun; no full-suite score is claimed. The old engineered-state scores are not substituted for missing Qwen evaluation.

[Run guide](docs/RUN_BROWSER_SUITE.md) · [All 102 tests passing, including Chrome](reports/tests-current.txt). A complete model benchmark needs a deployment with enough memory; the current local batch must not automatically restart.

## Original V1 result (preserved warm-up)

120,000 CPU training episodes across 12 policies; 473,212 environment steps. Each policy evaluated on the same 200 held-out worlds.

| Training arm | True success across seeds 11 / 22 / 33 |
|---|---|
| Outcome reward + memory | 100% / 100% / 100% |
| Outcome reward, no memory | 100% / 100% / 40% |
| UI-proxy reward + memory | 40% / 40% / 40% |
| UI-proxy reward, no memory | 40% / 40% / 40% |

The scripted verification baseline also reaches 100%. The environment is intentionally small and solvable; this is a reward-design/control study, not proof that RL beats scripting. UI-reward agents receive a deliberately flawed objective. Their high proxy reward and low true success demonstrate operational proxy exploitation, not intent. See the report for limitations and per-scenario evidence.

## Setup

Python 3.11+, [uv](https://docs.astral.sh/uv/), and Google Chrome installed locally:

```sh
git clone https://github.com/pallavisharma6802/ClickOnce.git
cd ClickOnce
uv sync --extra report
```

Chrome is detected automatically on macOS. Without Chrome, install Playwright Chromium with `uv run playwright install chromium`. No credentials, cloud services or paid APIs are needed. Ollama is optional for the visual path. That path expects the already-installed `qwen3-vl:2b`; the project does not automatically download it.

## Run tests

Fast simulator/learning tests (browser tests explicitly skipped):

```sh
uv run python -m unittest discover -s tests -v
```

Full real-browser suite:

```sh
CLICKONCE_BROWSER_TESTS=1 uv run python -m unittest discover -s tests -v
```

The CLI smoke test includes bounded RL training and checkpoint/evaluation artifacts. See [current test results](reports/tests-current.txt) and [the test plan](docs/TEST_PLAN.md).

## One-command reproduction

```sh
uv run --extra report python scripts/reproduce.py --output runs/full-reproduction
```

This runs the full test suite, all RL arms, paired evaluation, a browser demo, and a report. Optional `--vision` additionally runs the installed local VLM gate; it does not download a model. The primary dashboard links the original recorded replays; reproduction runs retain their own demo separately.

## Run the project

Open the synthetic booking application in a dedicated browser. This command owns the browser and local server; Ctrl+C closes both:

```sh
uv run python -m click_once serve --scenario committed_timeout
```

Reproduce all training arms, validation, held-out test and longer-delay stress evaluation in a **fresh** output directory:

```sh
uv run python -m click_once train --output runs/reproduction --episodes 10000 --eval-count 200
uv run --extra report python -m click_once report --experiment runs/reproduction --output reports/reproduction
```

Record an actual browser episode using the first training seed, without picking the best checkpoint:

```sh
uv run python -m click_once demo --output runs/my-demo --scenario committed_timeout \
  --policy outcome-memory-seed11 --checkpoint runs/experiment-v2/q_strict_memory_11.json
```

Run the frozen local VLM gate, then a screenshot-driven agent episode:

```sh
uv run python -m click_once vision --output runs/my-vision
uv run python -m click_once demo --output runs/my-visual-demo --scenario pending_timeout \
  --policy frozen-qwen-plus-learned-policy --checkpoint runs/experiment-v2/q_strict_memory_11.json --vision
```

The visual model is automatically unloaded when its command exits. Inference is local, one request at a time, with a 90-second request timeout and one bounded malformed-output retry. Cache keys include image bytes, model, prompt and output schema. Fresh latency and cache hits are recorded separately.

## Architecture

```text
Private scenario + booking records
             ↓ public UI projection
       Local browser / screenshot
             ↓
 Structured UI or frozen VLM perception
             ↓
   Public action memory + learned policy
             ↓
      Allowlisted browser control
             ↓
      Next state and training reward

Private records → independent evaluator → metrics
                 (never policy input)
```

- `click_once/env.py`: state transitions, observations and training rewards.
- `click_once/evaluator.py`: independent record-level outcome checks.
- `click_once/gym_env.py`: Gymnasium API wrapper.
- `click_once/learning.py`: finite-memory Q-learning and labeled scripted baselines.
- `click_once/experiment.py`: disjoint seed manifests, training, paired evaluation, raw artifacts.
- `click_once/browser.py` + `web.html`: loopback UI and browser executor.
- `click_once/perception.py`: frozen local screenshot reader and engineering gate.
- `click_once/demo.py`: actual browser recording and replay.
- `click_once/reporting.py`: metrics, figures and results dashboard.
- `click_once/resources.py`: process-tree RSS/global memory pressure guard.

## Artifacts and safeguards

Primary results: `runs/experiment-v2/` (config, manifests, checkpoints, curves, episode CSV, public trajectories and separate evaluator-only audits). Development attempts remain available locally under `experiment-v1` and `vision-v1`; they are excluded from Git. See `docs/DECISIONS.md` for the corrections. Private-audit filenames mean evaluator-only synthetic records, not personal data.

No Fusion, OSWorld, Kaggle or background automation. Training is single-process CPU. CLI workloads sample memory every three seconds and interrupt on two consecutive critical macOS pressure samples. No automatic restart. Resource RSS covers this process tree; Ollama runs externally, so global pressure/swap are the system-wide indicators.

No real transactions or account access. Browser routes expose public UI data, not audits or rewards. The evaluator boundary is not a hardened adversarial sandbox. Do not use this app for real bookings.

## Scope and next work

The current four actions are Submit, Check history, Wait, Finish. Arbitrary pixel grounding, free-form task understanding, UI-layout generalization, full VLM SFT/RL and robust deployment remain future work. The task generator makes the first submit faulty and subsequent submits successful; real workflows are more complex. These limitations are deliberate and reported.

The research question is whether different reward designs train different behavior under ambiguous outcomes, and whether simple memory improves stability. It is **not** whether a new architecture beats frontier agents. Relevant prior work and experiment assumptions are linked in `docs/PLAN.md`.
