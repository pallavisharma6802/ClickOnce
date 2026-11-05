# Run the five-family suite

Install Python dependencies with `uv sync --extra report`, install local Google Chrome, and start Ollama. Download the free local model with `ollama pull qwen3-vl:2b-instruct` (about 2 GB). No paid API or personal login is needed. Do not run Fusion or other model jobs alongside this on an 8 GB Mac.

```sh
uv run python -m unittest discover -s tests -v
CLICKONCE_BROWSER_TESTS=1 uv run python -m unittest tests.test_suite_ui -v
uv run python -m click_once.suite_eval validate --output runs/my-validation
uv run python -m click_once.suite_eval calibrate --output runs/my-development
uv run python -m click_once.suite_eval run --output runs/my-suite
uv run python -m click_once.suite_report --experiment runs/my-suite --output reports/my-suite
```

Output directories must be new; there is no silent overwrite or automatic restart. Inspect the separate development result before running the scored suite. Do not tune prompts or tasks from scored outcomes and relabel them as a fresh test. The model is frozen; this suite does not train its weights.

Each attempt records public instructions, screenshots, actual actions, model timing and an independent grade. Evaluator-only catalogs/answers and saved artifacts are stored separately from agent inputs. The agent sees only the current screenshot, public tabs, its own memory and recent actions. Website setup uses Playwright; screenshot actions use actual mouse/keyboard operations.

The memory guard records global pressure/available memory and process-tree RSS. Ollama is a separate service, so process-tree RSS alone excludes the model: use global pressure when assessing safety. Two critical samples or an unavailable pressure query stop the workload. Do not automatically resume a memory-stopped run. Model unload is attempted on exit. Check `ollama ps` afterward.

Wikipedia needs internet access and may change. Setup/network failures are visible infrastructure outcomes, not evidence that the model cannot navigate. Local email tasks save synthetic drafts and have no send control. No purchasing or personal-account changes occur.

`BrowserTaskEnv` exposes Gymnasium `reset`/`step` with screenshot observations and JSON actions, a small step cost and terminal artifact reward. This is an environment interface for future RL experiments, not a claim that Qwen was RL-trained here. Real VLM policy training would be a separate GPU experiment.
