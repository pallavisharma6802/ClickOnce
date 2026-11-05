# Implementation and experiment plan

## Objective and scope

Build a reproducible, Gymnasium-compatible browser environment in which an agent must complete exactly one booking despite uncertain UI feedback. Demonstrate reward-driven learning, evaluate reward exploitation, and optionally attach a frozen local VLM. All transactions are synthetic. The first release has one task family, five failure modes, no real accounts, no VM and no paid APIs.

Pitch: “I built an RL environment that teaches computer-use agents when not to click again: the same timeout may mean failure, pending work, or a successful booking.” This is a proposed experiment, not an established result. Generic recovery, reward hacking, and idempotency have substantial prior work; no first-ever claim.

## Architecture

Seeded scenario generator -> private booking state machine -> public UI projection -> local browser.
Public observation -> perception adapter -> action memory + learned policy -> bounded GUI action -> environment transition.
Private audit -> reward provider during training / independent outcome evaluator during evaluation.
Trajectory recorder captures public observations, actions, rewards and timestamps. Private audit lives in a separate artifact explicitly marked evaluator-only.

Initial learner: finite-memory tabular Q-learning over public UI features, with no GPU requirement. A memoryless Q learner is an ablation; a scripted check-history policy is a sanity baseline, not a learned result. A recurrent neural policy is optional only after the tabular experiment establishes the environment is learnable. This choice isolates reward/environment design without spending hours on perception.

VLM path: frozen local VLM reads actual browser screenshots into a bounded public observation schema. Validate perception accuracy and latency before allowing it to control actions. A result using structured UI observations must never be called visual-agent performance. VLM adapter SFT/RL training is a separate optional phase requiring a measured memory/rollout budget; do not silently substitute small-policy training for VLM training.

## Milestones, gates and deliverables

### M0 — specification and tests (current)
- Write environment, reward, data-split and resource contracts.
- Write executable acceptance tests before implementation.
- Run tests once to demonstrate honest red status; record baseline.
- Deliver docs/PLAN.md, ENVIRONMENT.md, TEST_PLAN.md and tests/.
Exit: requirements are explicit and failures point to missing components, not unexplained behavior.

### M1 — deterministic environment and independent evaluator
- Implement five scenarios, bounded actions, public observations, append-only audit and reward providers.
- Wrap with Gymnasium API: reset -> (observation, info); step -> (observation, reward, terminated, truncated, info).
- Validate contract suite and Gymnasium environment checker.
Exit: every scenario is solvable through public observations; ambiguous cases have identical observations until inspection; exploit policies cannot pass strict evaluation; same seed/action sequence reproduces outcomes.

### M2 — real browser surface
- Serve a small booking page on loopback; buttons execute state-machine transitions.
- Use one Playwright browser with a fixed viewport; record screenshots and coordinates/element actions.
- State used for grading is not exposed through the browser or policy payload. UI may expose legitimate booking history.
- One scripted successful browser episode per scenario proves transition/UI parity. Replay viewer shows agent screen beside separately labeled audit reality.
Exit: all browser acceptance tests pass. Browser UI state, simulator projection and executed action trace agree. Public page contains no scenario label or hidden reward outcome.

### M3 — learning and experiment pipeline
- Train finite-memory and memoryless Q-learning baselines using real reward updates.
- Build seed manifests before training. Train worlds: 0–9999; validation: 10000–10999; locked test: 20000–20999. Final evaluation uses exactly the same scenario instances for every policy. Each split is balanced by scenario, with sampled delays and task identities.
- Use validation only for algorithm/configuration choices. Run final test once after configurations are frozen; retain all intermediate configs and failed runs.
- Reward arms: terminal UI-proxy reward vs terminal strict-outcome reward. Same action costs, algorithm, training interaction budget and episode limits. Keep raw reward on its own scale; do not subtract unlike scales and call that an exploit rate.
- Proposed starting budget: 3 independent training seeds, 10000 episodes each, both reward arms. Run a 500-episode pilot first and estimate runtime; reduce or expand only with a recorded reason. CPU, one worker.
- Baselines: random, stop-on-success/retry-on-timeout, scripted verify-before-retry, untrained policy; trained memory and no-memory policies under each reward.
Exit: checkpoint reload reproduces predictions; learning curves and weight/Q-value changes exist; training/test separation passes; report per-scenario results even if no improvement.

### M4 — frozen VLM bridge (conditional)
- Check existing local model availability without downloading another model automatically. Use qwen3-vl:2b only if it fits alongside one browser.
- Measure cold vs warm latency and peak memory on 20 screenshots balanced across visible states. Reuse identical image results by content hash; include cache hit rates and exclude cached timings from fresh inference latency.
- Require >=90% exact match on decision-relevant visible state labels on this small smoke set, zero malformed accepted actions, and no critical memory pressure. This is a go/no-go engineering criterion, not a research conclusion or general accuracy claim.
- If gate fails, report why and keep structured-observation findings explicitly limited. Do not force an hours-long run or use a paid service.
- VLM controls browser only via parsed, allowlisted actions; no generated Python/JS execution. Policy evaluation gets no private audit or reward.
Exit: screenshot-to-perception-to-action-to-browser-to-evaluator trace exists and is visually reviewed. Clearly separate perception errors from control errors.

### M5 — final evidence and report
- Export JSONL trajectories, per-episode CSV, per-seed learning curves, aggregate/per-scenario metrics, and reproducible commands.
- Show paired replay of baseline failure and learned behavior only if those behaviors actually occurred; do not stage a scripted policy as a learned policy.
- README describes setup, exact observation/action spaces, RL target, reward assumptions, holdouts and limitations. Include null results and inference/resource overhead.
- Source references and relation to existing recovery/reward-hacking work.
Exit: clean install, full tests, one-command bounded experiment reproduction, actual report and replay artifacts.

## Metrics and preregistered comparisons

Primary: strict completion rate (exactly one correct confirmed booking, no pending submissions, no duplicate ever created). Secondary: duplicate-episode rate, false-completion rate, mean actions and verification actions, timeout/truncation rate, return, wall-clock latency and memory. Reward exploitation metric: fraction of episodes with positive terminal proxy reward and strict failure. This is operational proxy exploitation, not evidence of intent.

Compare strict-trained vs proxy-trained under the same strict evaluator; memory vs no memory; learned vs scripted verification. Report all three training seeds individually plus aggregate uncertainty. Paired bootstrap over held-out scenario instances can describe instance uncertainty; do not pretend it captures training-seed uncertainty. Separate familiar-distribution test results from stress tests on longer delays (6–8 ticks) and changed visual layouts.

Do not require an arbitrary performance gain for the project to pass. M1–M3 correctness and reproducibility are acceptance conditions; learning superiority is a hypothesis. Sparse-reward learning can fail; debugging cannot use locked test data.

## Resource and authorization limits

8 GB Mac: no Fusion/OSWorld, one browser, one optional local VLM, CPU-only baseline learner, no parallel rollout workers. Browser closed after use. No real payments, messages or bookings. Dependency downloads only; no paid API calls or large new model downloads. Secrets remain outside source and logs.

Resource gate: record process RSS and macOS pressure every 3 seconds during live workloads. Two consecutive critical-pressure samples stop the workload and unload this project's model. No automatic restart. Initial training smoke timeout 60 seconds; browser smoke 120 seconds; local VLM request timeout 90 seconds. Run fresh inference timing separately from UI timing. Measure before setting a final training budget.

## Sources

Gymnasium API: https://gymnasium.farama.org/api/env/
Gymnasium termination/truncation: https://gymnasium.farama.org/tutorials/gymnasium_basics/handling_time_limits/
MiniWoB++: https://github.com/Farama-Foundation/miniwob-plusplus
AgentHijack: https://proceedings.mlr.press/v306/sun26ba.html
ReTrace: https://arxiv.org/abs/2610.27954
Hack-Verifiable Environments: https://arxiv.org/abs/2605.20744
Stripe idempotency: https://docs.stripe.com/api/idempotent_requests
