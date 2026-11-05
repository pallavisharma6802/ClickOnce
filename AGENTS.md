# Working agreement

Follow docs/PLAN.md milestone order. Write or revise the relevant acceptance tests before behavior changes. Never weaken a test merely to make implementation pass; document justified contract changes in docs/DECISIONS.md.

Keep simulations local and synthetic. Do not restart OSWorld, Fusion, or Kaggle. No cloud spend or credential use without the user's explicit authorization for the particular service. Do not read or log secret values. One browser, one inference request, no parallel training workers. Use CPU for the small-policy baseline.

Policies may receive only public observations, previous actions, and training rewards. Private fault labels, backend audit data, pending job schedules, held-out seeds and ground-truth completion labels are evaluator-only. Do not accidentally pass Gym info or debug state to an agent or a VLM.

Report trained components precisely. Tabular/MLP/GRU policy training is not VLM fine-tuning. Demonstrations are not RL. Proxy reward is not task success. Do not claim novelty or an improvement without supporting experiments. Preserve unsuccessful runs and raw metrics. Do not tune on the locked test split.

Keep machine resource measurements, configuration and seed provenance with each experiment. Stop workloads on sustained critical macOS memory pressure. Do not automatically restart after a resource stop.
