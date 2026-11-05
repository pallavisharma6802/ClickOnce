# V2: evidence freshness and target-aware retries

V1 remains intact as a correctness baseline. V2 is a new environment and new evaluation protocol, not a retrospective change to v1 scores.

## Diagnosis
Two public-action probe sequences over 100 train and 100 test worlds each produced eight distinct policy feature states in each split. Every probed test state was already in training. This is a probe-based coverage diagnostic, not exhaustive reachability analysis. The learner discarded goal identity; only the first request could fail; history was immediate and authoritative; there were no unrelated bookings. The 100% result establishes learnability of a tiny state machine, not general computer use.

## New capabilities
1. Repeated submission faults: 0–3 failures may precede a valid commit. No guarantee that attempt two works.
2. Target-aware evidence: 0–3 unrelated preexisting bookings, including a similar room/request name. Only the requested record counts; unrelated records must be preserved.
3. Stale history: history is an explicit snapshot 0–3 action ticks old. A visible freshness panel supplies current tick, snapshot tick and last submission tick. An empty snapshot older than the latest submission is not evidence that submission failed.
4. Compound cases: repeated faults + stale history + distractors + pending completion. Keep individual tiers to explain failure causes.

Every episode retains a publicly observable route to completion. Delays and retries are bounded; a conservative public-only policy provides a solvability witness under the 24-action limit. Never make hidden information unobservable just to lower scores. This remains a semantic-action control study, not pixel-level VLM RL.

## Frozen protocol
- Tiers: clean, repeated, distractors, stale, combined.
- Development train seeds: 100000–109999. Validation: 200000–200999. New locked test: 300000–300999. No overlap with v1 policy training/test or screenshot fixtures.
- Pilot and diagnose on validation only. Freeze control configurations before opening the new test split.
- First compare frozen v1 policies through a documented observation adapter (new freshness fields omitted; original information retained). Exceptions are errors, not silently dropped episodes.
- Add a target-aware, freshness-aware Q-learning baseline. It uses visible target string matching and timestamps; these are engineered features and must be reported as such. No pretrained VLM improvement claim.
- Control baselines: old verification rule, target-only verification, freshness-aware verification. Compare the same target-aware learner with and without freshness information under identical transitions and budgets.
- Three seeds 11/22/33; fixed 10000 training episodes per seed/arm initially. Same step cost, action limit, training worlds and episode counts; report transition counts. Outcome reward only; v1 already establishes proxy-reward exploitability.
- Primary metrics: exact outcome success, duplicates, false completion, truncation, actions and verification count, per-tier and per-seed. Independent evaluation checks target records AND preservation of all initial unrelated bookings.
- No desired failure percentage. If the new experiment saturates, report the ceiling rather than deliberately sabotaging the agent. Strong scripted baselines are necessary; the goal is to explain what representation/control mechanisms are needed.

## Remaining frontier
This release does not establish general semantic transfer, visual grounding, recurrent neural learning or realistic multi-app competence. A serious follow-up needs held-out app templates and screenshot-driven evaluation rather than more seed changes. Scaling a toy generator is not a substitute.

Related methodology: procedural train/test separation in Procgen, https://proceedings.mlr.press/v119/cobbe20a . New seeds alone do not establish structural generalization.
