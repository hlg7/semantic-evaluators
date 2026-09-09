# Provenance and validation limits

The default rule text, category definitions, scorer behavior, checkpoint revisions and detector thresholds originate from the final v3 evaluator in [hlg7/star-semantic-experiments](https://github.com/hlg7/star-semantic-experiments/tree/b9d9ea6), consolidated September 9, 2026. Original source files include `semantic_scoring.py`, `run_semantic_full.py`, `data/semantic_eval_v2/build.py`, `data/semantic_eval_v3/build.py` and the pinned evaluation configuration.

This repository is a standalone refactor: no STAR model, generation hook, mask schedule, scene dataset, model weights, private credentials or experiment images are required. The source research repository retains its frozen code and results. The new protocol name is `six_semantics_v1`; the historical imported checks retain `semantic_eval_v3_exploratory`.

The previous study evaluated 6,000 canonical images with 5,999 valid primary scores and one invalid color answer (`silver`). Prior development/held-out AI reviews exposed identity confusion, sparse clear count labels, surface-texture disagreements and category ambiguity. No category passed every prespecified screen. The held-out findings informed the final v3 revision, so that split does not independently validate v3 or this refactor.

Validation for extraction includes model-free tests covering six tasks, answer isolation, unseen nouns, schema failures, arbitrary image dimensions, SHA checks, correct baseline pairing, atomic/resumable runs, error-history preservation and output locks. Frozen source predictions are replayed through the extracted scorer to check score preservation; this does not retest visual perception. No new GPU model inference has been performed through the standalone package while the Pod is stopped.

For a new backbone, keep evaluator rules/configuration fixed across compared conditions and inspect a calibration sample from that image distribution. General code and task definitions do not guarantee calibrated accuracy across generators, resolutions, subjects or styles. Unknown rates are model behaviors, not ground-truth uncertainty. Preserve failure cases and avoid presenting exploratory automated scores as validated human judgments.

Model names and pinned revisions are references to third-party model artifacts; their licenses and usage terms remain separate. No weights are redistributed here.

## Extraction checks completed

19 model-free tests pass. All 300 historical compiled tasks validate; replay of all 5,999 valid original predictions yields exactly the same scores, and the single invalid color answer remains rejected. The STAR importer preserves all 6,000 original compiled checks. See [machine-readable verification](replay_verification.json). Package installation and the CLI were checked locally; these checks do not establish new GPU adapter equivalence or visual accuracy.
