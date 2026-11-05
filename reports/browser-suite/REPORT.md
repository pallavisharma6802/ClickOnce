# Five-family screenshot-agent pilot

2 of 30 planned cases have a recorded outcome. One actual frozen-Qwen attempt per case; no RL or VLM training in this suite.

Math, booking, email and offer sites are local benchmark applications on separate origins. Wikipedia navigation uses the live external site. Email is a synthetic local saved draft, not Gmail.

| Family | Passed / scorable | Infrastructure | Attempted / planned |
|---|---|---|---|
| booking | 0 / 1 | 0 | 1 / 6 |
| math | 0 / 0 | 1 | 1 / 6 |
| wiki | 0 / 0 | 0 | 0 / 6 |
| email | 0 / 0 | 0 | 0 / 6 |
| offers | 0 / 0 | 0 | 0 / 6 |

**Run stopped:** Manual resource-safety stop after one completed case: global swap grew rapidly and per-action latency increased. No sustained-critical-pressure auto-stop was triggered. Model was unloaded; no automatic restart.


Infrastructure errors and interrupted runs cannot establish model capability. Budget exhaustion, malformed actions and premature completion are agent failures. Thirty curated cases are a pilot, not a general reliability estimate. Difficulty labels are authored bands, not calibrated human difficulty.

## Per-case evidence

| Case | Outcome | End condition | Actions |
|---|---|---|---|
| [booking-easy-0](booking-easy-0/index.html) | FAIL | action_budget | 24 |
| [math-easy-0](math-easy-0/index.html) | INFRASTRUCTURE | interrupted | 2 |

## Interpretation

Inspect recorded actions and independent checks before assigning a cause. Any failure labels derived from traces are analyst candidates, not human ground truth. No unsuccessful result is automatically a near miss. The historical tabular RL study is reported separately in ../evaluation/REPORT.md.

Reproduce after Ollama has qwen3-vl:2b-instruct installed:

```sh
uv run python -m click_once.suite_eval validate --output runs/new-validation
uv run python -m click_once.suite_eval run --output runs/new-suite
uv run python -m click_once.suite_report --experiment runs/new-suite --output reports/new-suite
```
