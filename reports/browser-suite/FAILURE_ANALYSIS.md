# Evidence-based failure notes

The benchmark is incomplete. These observations do not estimate Qwen capability across five families.

## Completed scored case: booking-easy-0

Observed: 24 actual actions, all clicks at the same normalized location. The clicked control was Submit booking. Independent backend evidence contains 24 confirmed target bookings, hence 23 extra bookings. The agent never checked history or finished the task. The 24-action cap stopped the attempt.

Candidate behavioral labels: repeated non-idempotent submission; failure to use available outcome-verification control; failure to recover from feedback. These are trace-based analyst labels, not independently annotated human ground truth. The evidence does not establish why the model repeated itself or whether a different model/prompt would solve it. This was a straightforward no-fault case, so making the scenario harder is not the immediate bottleneck.

## Interrupted scored case: math-easy-0

The batch was interrupted for resource safety while the next attempt was running. This is infrastructure censoring, not a math-reasoning failure and not a scored success. Twenty-eight additional cases were never started.

## Unscored development checks

Full-resolution Thinking and Instruct attempts timed out before any action. The smaller-image deployment produced actions. An early action schema omitted coordinates; requiring all generation fields corrected that adapter problem before scored evaluation.

On a separate development puzzle with numbers 1, 1, 4, 6, Qwen chose a button instead of the text field, typed without focus, and repeatedly clicked the button. The saved expression remained empty. Its proposed expression `6 * (4 + 1) / 1` also equals 30, not 24. Grounding and arithmetic errors are separate observations; no points are awarded for a claimed unsaved solution. The development fixture is not included among the 30 cases.

## Resource evidence and limits

The scored batch's global swap rose from 10,007,019,520 to 18,839,044,096 bytes. Pressure samples were 1 or 2; no sustained-critical-pressure stop was triggered. The operator stopped the batch based on rapid paging growth and rising latency, and verified Ollama had no loaded models afterward. Swap is system-wide and cannot attribute every byte to Qwen; process-tree RSS excludes the separate Ollama service. The deployment was unsuitable for completing this batch while keeping this Mac responsive.

Next evaluation requires a resource-safe model deployment and a newly declared run. Do not treat missing cases as failures or silently pool another model/configuration into this run. VLM training and learned reward models remain future work; the current suite is an environment and frozen-agent evaluation harness.
