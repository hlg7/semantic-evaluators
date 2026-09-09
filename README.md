# Semantic Evaluators

A backbone-independent evaluator for six aspects of generated images. Provide **images and structured targets**; the package observes each image, scores the answer and summarizes results. It supports STAR and other generators without requiring a particular image size, scale count or generation format.

## What the six evaluators check

| Semantic | Tool | Core question |
|---|---|---|
| Object | Grounding DINO | Is the requested object present or absent? |
| Color | Qwen3-VL | Does its main exterior color match the target? |
| Shape | Qwen3-VL | Does its overall outline match the target? |
| Texture | Qwen3-VL | Does its pattern or surface roughness match the target? |
| Count | Grounding DINO | Does the detected count equal the requested count? |
| Spatial relation | DINO for 2D; Qwen for depth/containment | Does the relation between A and B match the target? |

## Three shared conventions

1. Identify objects before judging attributes or relations. These tasks require a unique referent; multiple candidates remain ambiguous. Existence accepts any instance, and count includes all detected instances.
2. A confirmed match scores **1**. A mismatch, missing object, ambiguity or unclear observation scores **0**, with these states reported separately. Detector existence/count estimates do not abstain.
3. Invalid answers and execution errors have **no score**. They are recorded and excluded from means, with valid denominators reported.

These are **exploratory automatic scores, not validated human accuracy**. General interfaces do not guarantee reliable perception across backbones or datasets.

## Input and output at a glance

Input is JSONL, one image/task per line. For example:

```json
{"id":"color_001","image":"images/car.png","semantic":"color","objects":["car"],"expected":"red"}
```

The expected answer is used only by the scorer, not passed to the model. Texture and spatial tasks also specify a subtype. Optional metadata records backbone, prompt, seed and condition; `baseline_id` enables paired comparisons. One image may appear in several tasks with different IDs.

Outputs include per-image observations, raw answers/detections, scores and errors, plus grouped success rates, uncertainty and coverage. Optional baseline comparisons give paired change and retention; count also reports deviation from the requested count. No image, model weight or STAR result dataset is bundled.

## Choose the level of detail

| Need | Read |
|---|---|
| Understand the evaluator | This page |
| Look up precise category definitions, answer vocabularies or scoring conventions | [Complete semantic rules](docs/evaluators.md) |
| Check model revisions, thresholds, response parsing or resume behavior | [Parameters and engineering](docs/engineering.md) |
| Install, run, or import the existing STAR experiment | [Run guide](docs/usage.md) |
| Prepare input files or consume results | [Input/output contract](docs/interface.md) |
| Understand verification and known limits | [Provenance](docs/provenance.md) |

Start with the run guide for `validate → run → summarize`. Validation and aggregation work locally; model inference requires CUDA. The original experiment and its 6,000-image results remain in [star-semantic-experiments](https://github.com/hlg7/star-semantic-experiments).
