# Manifest and result contract

The input is UTF-8 JSONL, one object per nonblank line. IDs are unique strings matching `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`. Absolute image paths are supported; relative paths resolve from the manifest directory unless `--image-root` is supplied. Multipage/animated images are rejected.

| Field | Required | Meaning |
|---|---|---|
| `id` | Yes | Unique evaluation-row ID, safe as an output filename |
| `image` | Yes | Image file path |
| `semantic` | Yes for generic records | `object`, `color`, `shape`, `texture`, `count`, `spatial_relation` |
| `objects` | Yes for generic records | One canonical singular noun; two ordered nouns A, B for a relation |
| `expected` | Yes for generic records | Typed reference value; visible only to the scorer |
| `subtype` | For texture/relations | Texture: `pattern`, `surface`; relations: `left_right`, `above_below`, `front_behind`, `containment` |
| `baseline_id` | No | Another row in this manifest, or own ID for a baseline |
| `metadata` | No | Experiment labels; not passed to models |
| `image_sha256` | No | Expected SHA-256 of image file bytes |
| `check` | Alternative to generic task fields | Complete compiled check from a trusted protocol/import; retains exact model prompts |

Default subtypes for other tasks: object=`identity`, color=`color`, shape=`outline`, count=`single_category`. A compiled check is validated but its text is not regenerated; users are responsible for its rule provenance. When `check` is supplied it takes precedence over generic task fields.

Reference values: object uses JSON `true`/`false`, count uses a nonnegative integer (not a bool), and all other tasks use the categorical strings listed in [evaluator rules](evaluators.md). The generic interface supports testing absence and counts beyond the source experiment's 2–6 range.

No `expected` field is passed to the backend. `protocol.observation_task` restricts inputs to the semantic, subtype, identity-validation flag and evaluator question/definitions. Model output validation and target matching are separate operations.

A successful prediction stores `id`, input/file hashes, task/tool, metadata, optional baseline, `observation`, raw response/detections, response `attempts`, status, binary `success`, and optional `absolute_error`. Evaluation errors have `success=null`; retries preserve `previous_errors`. Missing objects/ambiguous/unclear observations have zero confirmed success, with their statuses retained.

`manifest.json` binds results to the complete compiled inputs, file hashes and sizes, actual package versions, model configuration and package source hashes. Changed code/config/input/dependency versions require a new output directory. Image data is rechecked before prediction. Fatal image mutation or model-loading/OOM errors stop execution; existing atomic results remain resumable. Schema/per-image backend failures are recorded as evaluation errors. No failed result is silently called a success.

Summaries preserve all rows, including missing predictions. Aggregation groups by semantic/subtype and optional `metadata.backbone`/`metadata.condition`. Missing labels become `unspecified`; callers should supply backbone/condition labels when combining experiments. Other metadata remains available in `results.jsonl` for custom analysis. Prefix/suffix scales are not built into this package.

Paired delta is intervention success minus baseline success, averaged over valid pairs, in **score units** (multiply by 100 for percentage points). Retention uses only valid pairs with baseline success=1. Count MAE compares estimated count to the requested count, not independently observed ground truth. All denominators are explicit. There are no automatic statistical significance claims.
