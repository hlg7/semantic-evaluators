# Installation and run guide

[Quick overview](../README.md) · [Semantic rules](evaluators.md) · [Parameters and engineering](engineering.md) · [Input/output contract](interface.md)

## Install

Python 3.10+ is required. Python 3.12 is suitable for the GPU environment.

```bash
git clone https://github.com/hlg7/semantic-evaluators.git
cd semantic-evaluators
python -m pip install -e .
```

Validation, scoring logic, summaries and tests run without CUDA. For model inference, use a separate CUDA environment with a matching PyTorch/torchvision pair, then install:

```bash
python -m pip install -e '.[inference]'
```

PyTorch/torchvision are intentionally not installed by this package because their builds must match your GPU environment. The adapters load one model at a time. First inference downloads the pinned Hugging Face checkpoints; set `HF_HOME` to persistent storage. Model licenses and access terms apply separately.

## Describe your images

Use JSONL: **one image/task observation per line**. Paths are relative to the manifest, or to `--image-root`. Supply canonical singular object names rather than relying on a pluralizer.

```json
{"id":"car_base","image":"images/base.png","semantic":"color","objects":["car"],"expected":"red","metadata":{"backbone":"my_model","prompt_id":"p1","seed":42,"condition":"baseline"}}
{"id":"car_edit","image":"images/edit.png","semantic":"color","objects":["car"],"expected":"red","baseline_id":"car_base","metadata":{"backbone":"my_model","prompt_id":"p1","seed":42,"condition":"intervention"}}
```

A single image can be assessed on several semantics using different IDs/rows. Expected answers are explicit annotations supplied by the experiment; the package does not infer targets or text-token spans from free-form prompts.

There is no required scale count, sample count, seed, backbone name, 256×256 size, `runs.jsonl`, or generation tensor hash. Static RGB-convertible images are accepted at their actual dimensions; model processors perform their own resizing. EXIF rotation is not applied. Optional `image_sha256` is the SHA-256 of the **file bytes**.

## Validate, run and summarize

```bash
# Local, no models loaded:
semantic-evaluators validate --manifest experiment.jsonl

# CUDA host, one model at a time:
semantic-evaluators run --manifest experiment.jsonl --output outputs/experiment

# Local or CUDA host, no models loaded:
semantic-evaluators summarize --output outputs/experiment
```

`python -m semantic_evaluators ...` is equivalent. `--tool grounding_dino` or `--tool qwen_vlm` runs only that tool's assigned rows; use the same output directory for both, sequentially. The default `all` runs both. Use `--config path/to/config.json` to override pinned defaults; preserve a new output directory when changing the protocol/settings.

Results are written atomically under `predictions/`, with raw answers, attempts, hashes and metadata. Re-running the same inputs resumes valid successes and retries errors while retaining error history. An output lock prevents simultaneous writers. After a crash, verify the process has stopped before removing a stale `.running.lock`.

`summarize` writes `results.jsonl` and `summary.json`, with groups by semantic, subtype, backbone and condition. It includes valid/error/missing counts, confirmed success, uncertainty, missing-object frequency, optional paired change/retention and count-target deviation. It reports incomplete runs explicitly. Invalid answers are excluded, not assigned zero. Automatic ambiguity/uncertainty is not a confidence estimate.

Pairing is optional. A baseline must be in the same manifest with the identical evaluation task/reference. Supplied backbone, prompt ID and seed must agree when present on both records. The caller remains responsible for a scientifically meaningful experiment design.

## Repository structure

```text
semantic_evaluators/
  protocol.py       # Compile backbone-independent tasks; filter scorer data from model input
  rules.json        # General prompts, category definitions and attribute conventions
  defaults.json     # Pinned model revisions and default thresholds
  scoring.py        # Strict observation validation and exact-match/geometry scoring
  backends.py       # Lazy CUDA Grounding DINO and Qwen adapters
  io.py             # Manifest, image and baseline validation
  runner.py         # Provenance, output locks, atomic results and resume
  summary.py        # Generic groups and optional baseline-paired aggregates
  __main__.py       # CLI entry point
examples/           # Input manifest examples (provide your own image files)
docs/               # Complete evaluator rules, interface and provenance
tests/              # Model-free protocol and pipeline tests
```

Run tests with `python -m unittest discover -s tests -v`. No pretrained model or external image dataset is shipped here. Experiment 01 results are in [Infinity semantic-class masking](https://github.com/hlg7/infinity-semantic-masking).
