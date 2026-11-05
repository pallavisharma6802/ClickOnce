# Screenshot-driven five-family task suite — 2026-11-05

This defines an actual frozen-Qwen browser-agent evaluation to replace headline tabular-controller scores. Execution status is reported separately; a defined suite is not a completed model benchmark. Old RL studies remain available and are not relabeled as VLM results.

## Families and cases

30 explicitly authored cases: five families × three difficulty bands × two different instances. These are different goals/content, not repeated training seeds. One frozen model attempt per case; this is a small exploratory suite, not a population-level reliability estimate.

1. Booking: exactly-once completion with repeated faults, distractors, stale history and pending completion. Existing simulator, actual browser interface.
2. Math: interactive 24-game website. Easy direct arithmetic, medium grouped arithmetic, hard fractional intermediate results. Expression must use every displayed number exactly once. Independent AST/Fraction evaluator accepts alternative valid solutions.
3. Wikipedia: start on article X, reach article Y via actual article hyperlinks on live Wikipedia. No search, URL typing, direct navigation tool or external sites. Each case has a verified link-path witness unavailable to the agent. Difficulty bands are assigned path/interaction challenges, not a claim of proven shortest distance.
4. Source-to-email: read event facts, reconcile confirmed updates/suggestions and (hard) a separate venue bulletin, then save recipient/subject/body in a local draft-only mail site. The subject and body have separate fact checks, with superseded dates rejected. No real email or Gmail account is used for repeated benchmark runs.
5. Offer comparison: read a vendor website, exclude out-of-stock offers, calculate quantity/discount/shipping totals, and submit the cheapest eligible vendor and amount in a separate report website. Hard cases require a separate pricing-policy page.

Source and draft/report pages use separate local origins (ports). Case instructions explicitly forbid mentioning superseded dates/venues where the grader rejects them. Local pages are benchmark applications, not claimed replicas of real services. Wikipedia is a live external site; preserve URLs, timestamps and page hashes, and report drift/network/setup problems separately.

## Agent and boundaries

Model: qwen3-vl:2b-instruct, exact digest/renderer recorded. The pre-existing qwen3-vl:2b uses the Thinking renderer and timed out on a separate development fixture. The free 2B Instruct variant is downloaded for this new suite; this is a pre-benchmark deployment choice, not selection on scored cases. Prior Thinking results are retained and are not merged with these results. No VLM training.

Agent inputs: task instruction, current screenshot, viewport, active tab and public tab labels, last six actual actions. No DOM, private state, solution, witness path, reward, grader feedback, calculator or Python execution. Actions: normalized-coordinate click, type, allowlisted key, scroll, switch tab, wait, done. Wikipedia forbids typing/search and validates article-link transitions. Escape may close UI overlays; it is not navigation.

Common limits: 24 actions per episode, 300 seconds wall time, 60-second request timeout, 768 generated-token cap, one retry for malformed output. All action fields are required in the generation schema (unused fields get zero/empty defaults), avoiding optional-coordinate omissions observed only on the unscored development fixture. Stop after five consecutive identical actions on identical screenshots (a no-progress stop; ordinary pending-state updates are not blocked). Record protocol/malformed responses, resource caps and loop stops separately. Screenshots are downsampled to a maximum dimension of 768 pixels; coordinates remain normalized. Context is 3072 tokens, prompt batches 64 to reduce peak memory. These deployment settings were selected on development fixtures before scored evaluation. One browser and one model request at a time, memory guard, local weights unloaded at exit. No personal browser profile or credentials.

## Procedure and evaluation

Write tests and validate all case predicates first. Scripted reference interactions establish that the websites/forms work and cases have solutions; these are solvability tests, not agent scores or human baselines. Freeze the catalog, prompt, model identity and configuration before evaluating Qwen. If adapter calibration is needed, use separately labeled development fixtures and do not tune on final results.

Report each case and family as counts, with independent checks and failure types. No three-copy seed percentages, no claiming 30 independent training runs, no pooling this with engineered-state RL. Setup/website failures are reported and excluded only from the model-accuracy denominator with an explicit attempted-case count. Model output/protocol failures and agent budget failures remain unsuccessful agent attempts. Early verbal completion never passes a task by itself. Every successful episode needs an independent end-state check.

Save screenshots, real actions, model responses/timing, saved artifacts and evaluator-only evidence. User-facing reports must distinguish this 30-case pilot from a mature large benchmark. Do not make cases harder merely to force a target failure rate.
