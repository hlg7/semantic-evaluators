# Evaluator versions and validation limits

This package defines the backbone-independent `six_semantics_v1` protocol. Rule text and category definitions are in `semantic_evaluators/rules.json`; model revisions and detector thresholds are pinned in `defaults.json`. Compiled checks may retain their own protocol identifiers, including `semantic_eval_v3_exploratory`; those identifiers are part of the input contract and are not experiment numbers.

## Experiment 01: Infinity semantic-class masking

The first project experiment is [Infinity semantic-class masking](https://github.com/hlg7/infinity-semantic-masking): 300 prompts, seed 42 and 7,800 generated images. It uses an independent vendored evaluator, frozen checks and experiment-specific aggregation. Its repository contains the scores, curves, limitations and six audited output-category normalizations. Updating this general package does not automatically change that experiment's scores.

## Validation scope

Model-free tests cover six tasks, answer isolation, unseen nouns, schema failures, arbitrary image dimensions, SHA checks, correct baseline pairing, atomic/resumable runs, error-history preservation and output locks. Run `python -m unittest discover -s tests -v` to verify the current package. These tests check software behavior, not visual judgment accuracy.

Keep evaluator rules/configuration fixed across compared conditions and inspect a calibration sample from each image distribution. General task definitions do not guarantee calibrated accuracy across generators, resolutions, subjects or styles. Identity confusion, count errors, texture disagreement and category ambiguity remain possible. Preserve failures and report valid denominators; automated scores are exploratory rather than validated human judgments.

Model names and pinned revisions refer to third-party artifacts; their licenses and usage terms remain separate. No model weights are redistributed here.
