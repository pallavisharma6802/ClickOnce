# Test and evidence matrix

## Executable now

Run `python3 -m unittest discover -s tests -v`. Core contract tests depend only on Python's standard library. Missing implementation causes failures; they are not skipped or represented as passing. Experiment contract tests also remain red until their modules exist. Red baseline is saved in docs/test-baseline.txt.

| Requirement | Acceptance evidence |
|---|---|
| Scenario semantics | normal, failed, committed, pending and false-success transition assertions |
| Partial observability | identical full public payload for three ambiguous outcomes; legitimate inspection distinguishes them |
| Solvability | public-only scripted policy completes all five scenarios |
| No reward leakage | equal preterminal rewards across ambiguous cases; empty info |
| Reward exploits | stop-on-fake-success passes proxy but fails strict; duplicate retry fails strict; inspection/wait loops cannot farm positive reward |
| Episode lifecycle | invalid actions do not mutate; reset clears; seeded replay; terminal and truncation distinct; post-end step rejected |
| Outcome integrity | exactly one correct booking, zero pending, duplicate event preserved |
| Data separation | seed split manifests disjoint and balanced; same world across policy arms |
| Learning validity | one known Q update changes value correctly; checkpoint roundtrip; no reward/audit parameter in inference API |

## Add before implementing the corresponding phase

M1 Gym: environment checker, spaces containment for every scenario, wrapper string-action parity, termination/truncation bootstrap handling.

M2 Browser (real integration tests, not mocked): launch one browser; initial-state screenshot; click Submit; check History; compare rendered text/rows to simulator projection. Run all five scenarios. Ensure no private fields in HTML/network responses; page reload must not reset private outcome. Timeout paired screenshot hashes must match under fixed viewport. Check coordinates with actual element boxes. Test keyboard focus and reject clicks outside allowlisted controls. Browser and server close on failure. Public-only demonstration reaches each scenario's verified terminal state.

M3 Training: run tiny seeded training twice and compare checkpoints; greedy policy inference cannot receive reward, audit, scenario or seed. Record train seed, env-step count, config hash and checkpoint hash. Test Q bootstrap on truncation separately from terminal. Deliberately broken feature extraction must fail a boundary test. Evaluate frozen checkpoints on paired held-out manifests; metrics recomputed independently from raw audits; malformed/incomplete episodes counted, never dropped. Learning test proves updates, not a promised success rate. Scripted baselines and learned policies labeled distinctly.

M4 Perception: actual screenshot fixtures with manual visible-state labels; verify policy payload never includes hidden data. Timeout/backend-success and timeout/backend-failure images identical. Actual local VLM image request, JSON validation, timeout, one bounded retry on transient malformed output. Cache only by image + model + prompt hash. No action executes after invalid output. Log model ID and raw response without secrets. Report perception errors separately. Check Retina CSS-coordinate scaling before native execution (native desktop not initial scope).

M5 Experiment: full CLI smoke in a temporary output dir; config/manifest/checkpoint provenance; all episode rows retained; known aggregate fixture catches wrong denominators. Paired results retain seed and scenario. Report all individual training seeds; no per-seed best-checkpoint selection on test. Replay reads saved trace and does not fabricate model actions. README clean setup reproduced in project venv. Snapshot test protects report labels against calling structured observations VLM training.

## Resource tests

Start memory watchdog before real browser/model/training workloads. Mock critical-level readings to test stop-after-two behavior without exhausting RAM. Watchdog may stop only its own tracked process tree/model lease; never kill unrelated user processes. Record warm/cold inference separately and fail workload on the defined timeout. No stale server/browser/model after command exit. Do not add recurring monitoring unless requested.

## Research acceptance

Engineering correctness is mandatory; performance improvement is not. Freeze hypotheses, configs and splits before final test. If RL does not beat scripted verification, report that. If frozen VLM perception fails its gate, the project remains a structured-observation RL environment; no visual-control claim. VLM fine-tuning remains unfinished until actually performed and evaluated.
