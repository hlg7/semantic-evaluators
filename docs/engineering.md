# Parameters and engineering reference

[Quick overview](../README.md) · [Semantic rules](evaluators.md) · [Run guide](usage.md) · [Input/output contract](interface.md)

Use this page for exact configurations and execution behavior. Definitions of what counts as a correct observation are in the semantic rules. This documentation split does not change code, defaults or scores.

## Default models and parameters


| Setting | Value used |
|---|---|
| DINO checkpoint | `IDEA-Research/grounding-dino-base` |
| DINO model/processor revision | `12bdfa3120f3e7ec7b434d90674b3396eccf88eb` |
| Box / text thresholds | `0.30` / `0.25` |
| Per-query NMS IoU | `0.50` |
| Spatial center tolerance | `0.02` of width/height |
| Qwen checkpoint | `Qwen/Qwen3-VL-8B-Instruct` |
| Qwen model/processor revision | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` |
| Qwen image pixel limits | Minimum `65,536`; maximum `262,144` |
| Qwen decoding | Greedy (`do_sample=false`), maximum 192 new tokens |
| Inference | RunPod CUDA; DINO FP32, Qwen BF16 with SDPA |

DINO queries each noun independently as lowercase text with a final period. After processor postprocessing, decoded text labels must match the configured query/alias after lowercasing and word/whitespace normalization. NMS then removes overlapping retained candidates **within each query**, using detection scores. Boxes are not jointly deduplicated across different object categories. These fixed settings were not validated as optimal thresholds and do not vary by image or mask condition.

Each result is saved atomically. Resuming with identical inputs reuses successful records and retries error records while preserving prior failed attempts. Manifests reject changed inputs, code, dependencies or configurations in an existing output directory.

## Structured Qwen responses

Qwen is instructed to return JSON fields `identity_status`, `status`, `answer`, and brief visual `evidence`. For the final Qwen attribute/relation tasks, identity is `present`, `missing`, `ambiguous` or `unclear`. A non-present identity requires the same observation status and a null answer. Present identity can still have an unclear property. The parser checks allowed identity/status/answer combinations and answer categories; it does **not** verify the truth of the evidence text.

An invalid Qwen response gets **one fixed schema-reminder retry**. Both raw attempts are retained. If the retry is invalid, the record remains an error. There is no target-informed retry or post-hoc color mapping.

For non-`ok` observations, the answer must be null. Comparison is type-sensitive; arbitrary prose answers are not guessed. The shared parser supports lossless unsigned numeric-string conversion for Qwen count audits, but those audits are not part of the primary-only workload.

## Runtime and image handling

Python 3.10+ is required. Inference requires CUDA and a matching PyTorch/torchvision installation. Experiment 01 uses a vendored evaluator with its own pinned GPU environment; see the [Infinity experiment](https://github.com/hlg7/infinity-semantic-masking) and [verification scope](provenance.md).

Static RGB-convertible images are accepted at their actual dimensions. Models use their own processors for resizing. EXIF rotation is not applied; animated/multipage inputs are rejected. Image SHA-256 values refer to file bytes. Generation tensor hashes are distinct metadata.

## Provenance, resume and failures

`manifest.json` binds results to compiled inputs, image file hashes/sizes, package versions, model settings and source hashes. A changed input, dependency, code or configuration requires a new output directory. Input images are rechecked before prediction.

Results are saved atomically. Re-running identical inputs skips valid results and retries errors with `previous_errors` retained. Tools run sequentially, one model at a time. The output directory is locked against concurrent writers; after a crash, confirm the process has stopped before deleting a stale `.running.lock`.

Model-loading, OOM and image-mutation failures stop execution while preserving completed files. Per-image backend/schema errors remain explicit error records. Summaries distinguish missing output from an observed missing object, and exclude errors from score means. Use the [run guide](usage.md) for commands and [interface reference](interface.md) for fields.

## Source files

- [defaults.json](../semantic_evaluators/defaults.json): pinned models and numerical parameters.
- [rules.json](../semantic_evaluators/rules.json): exact question text and category definitions.
- [protocol.py](../semantic_evaluators/protocol.py): task compilation and model/scorer separation.
- [backends.py](../semantic_evaluators/backends.py): detector filtering, model calls and schema retry.
- [scoring.py](../semantic_evaluators/scoring.py): observation validation, matching and geometry.
- [runner.py](../semantic_evaluators/runner.py): locks, provenance and resumable results.
