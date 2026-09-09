# Complete semantic rules

[Quick overview](../README.md) · [Parameters and engineering](engineering.md) · [Input/output contract](interface.md)

These defaults derive from the STAR study's frozen v3 protocol. They are general task rules, not claims of validated accuracy on every backbone or dataset. See [provenance](provenance.md).

## Common observation rules

The model receives an image and the target category/task. Qwen also receives the allowed answer vocabulary and relevant category definitions. **The expected answer and generation condition are not included in model questions.** Reference answers are used by the scorer after observation; image IDs are join keys, not scoring rules.

The intended sequence is:

1. Establish object identity from visible evidence. Naming an object in a question does not establish that it exists.
2. Resolve the referent. Object existence accepts any instance; count considers all instances. Attribute and relation tasks require one identifiable instance of each named object. Multiple eligible instances are ambiguous even if their properties agree. The desired attribute or relation must not select the referent.
3. Observe the property or relation, using `unclear` when visual evidence is insufficient.
4. Compare the observation with the scorer-only reference answer.

The unique-instance requirement is an explicit operational convention, not a universal interpretation of singular language. Identity-first instructions do not guarantee correct perception. DINO uses retained detections to implement existence, count and uniqueness; it does not execute a separate reasoning-based identity check.

## Category definitions

These definitions apply consistently by noun across tasks and conditions, without image-specific exceptions.

| Category | Final interpretation |
|---|---|
| Notebook | Bound paper pages for writing; excludes laptops/notebook computers. |
| Plate | Shallow individual eating or serving dish. Excludes loaf pans, deep bowls, cutting boards, tables and solid pyramids. A rectangular plate is possible; outline alone does not establish identity. |
| Tray | Separate portable flat serving carrier, usually with a rim or handles. A tabletop itself is excluded. |
| Bowl | Open, relatively deep dish for food or contents. Distinguish from flower vases and cooking/loaf pans using visible structure; unresolved identity is unclear. |
| Vase | Upright vessel intended to hold flowers, identified from vessel structure. Desired position relative to another object is not an identity cue. |
| Picture frame | Physical border intended to hold a picture; excludes monitors, window frames and clock bezels. |
| Mirror | Reflective surface; excludes open doorways, windows and empty architectural openings. Unresolved reflection versus opening is unclear. |
| Sign | Physical information-bearing signboard or plaque; excludes pillars and architectural openings. |
| Remote control | Handheld device for operating equipment at a distance; excludes gamepads/console controllers. Unresolved device identity is unclear. |
| Pencil case | Small container or pouch for writing implements; not a computer, binder or unidentified box. |

Qwen receives relevant definitions in its system message. DINO receives category queries, **not these prose rules**. Its notebook query is `paper notebook`, with accepted decoded labels `paper notebook` and `notebook`; other queries accept their configured category label. This alias does not verify identity. DINO may still detect excluded objects, reflections or depictions, and cannot be assumed to enforce every semantic distinction above.

## Six semantic rules

### Object

Run the target-category query and apply the fixed detection/label-filter/NMS [detection procedure](engineering.md#default-models-and-parameters). At least one retained box yields `true`; no retained box yields `false`. The score is one when this Boolean matches the requested presence/absence reference, otherwise zero.

Multiple instances are allowed. No detection is a negative detection estimate, not proof that the object is absent. The detector does not provide an explicit `unclear` result for this task.

### Color

Judge the dominant visible **exterior material** of the uniquely identified object. Include permanently attached frames/body. Ignore small decorations, highlights, shadows, reflections, empty openings and contents seen through transparent walls.

For transparent material, use its tint only when the tint itself is visible; colorless transparent material is `other`. If no single exterior color dominates, use `multicolored`. Do not choose a part because its color matches the target.

Allowed answers: `black`, `blue`, `brown`, `green`, `orange`, `pink`, `purple`, `red`, `white`, `yellow`, `other`, `multicolored`.

Score by exact category match. This exterior-material convention can differ from ordinary whole-object appearance: sand inside an hourglass or liquid inside a clear jar does not determine its exterior color. An out-of-vocabulary answer is an evaluation error, not an automatically mapped synonym.

### Shape

Judge the overall boundary of the identified object, excluding printed patterns, holes, shadows, isolated parts and convenient faces of a different 3D object. Account for perspective only when the shape remains visually identifiable; otherwise use `unclear`.

Allowed answers:

- `round`: circular, rather than merely curved.
- `oval`: elongated rounded outline.
- `square`: square outline.
- `rectangular`: non-square rectangular outline.
- `triangular`: triangular overall boundary.
- `other`: a clearly observed shape outside these categories.

Score by exact category match. A triangular face on a pyramid does not establish a triangular plate. Missing or ambiguous object identity cannot produce confirmed shape success.

### Texture

Two subtypes are evaluated and reported separately:

| Subtype | Observation rule | Allowed answers |
|---|---|---|
| Pattern | Dominant repeated pattern on the object, not the background | `striped`, `checkered`, `polka-dotted`, `plain`, `mixed`, `other` |
| Surface | Roughness of the dominant visible surface area | `rough`, `smooth`, `mixed`, `other` |

For surface texture, rough requires visible grain, pits or irregularities; smooth requires a visibly even surface. Use `mixed` when substantial rough and smooth areas coexist without a dominant one. Material stereotypes, structural edges, lighting, blur and image sharpness alone are insufficient evidence. Use `unclear` if the surface cannot be judged.

Score by exact category match. Keep pattern and surface tasks separate in reports; the number of records is unrestricted.

### Count

The intended target is all recognizable physical instances in the whole image, including background and recognizable partially visible instances, excluding reflections and depictions. **The implemented estimate is the number of retained DINO boxes after label filtering and NMS.** There is no additional mechanism guaranteeing that every retained box is physical or every instance is detected.

The output is a nonnegative integer, including zero, with no restriction to the prompt's requested range of two through six. Multiple instances are the subject of this task and do not trigger ambiguity. DINO always returns a numeric estimate; it does not abstain on uncertain counts.

- Primary score: one if the estimated count equals the requested count, otherwise zero.
- Additional metric: `abs(estimated count - requested count)`, averaged with numeric coverage.

This additional metric is deviation from the requested count, **not counting error against independently annotated image ground truth**.

### Spatial relation

Identify both A and B before judging the relation. Missing either produces `missing`; multiple eligible instances produce `ambiguous` under the fixed unique-referent convention.

**2D position — Grounding DINO.** Query A and B separately. If either has no retained boxes, return `missing`; otherwise, if either has more than one, return `ambiguous`. For exactly one box each:

- Compute the difference between box centers, normalized by image width for horizontal relations or height for vertical relations.
- If the absolute difference is **less than 0.02**, return `aligned`.
- Otherwise, negative horizontal difference means `left`, positive means `right`; negative vertical difference means `above`, positive means `below`.

Coordinates are from the viewer's perspective, with image y increasing downward. Allowed answers are `left/right/aligned` or `above/below/aligned`, according to the task. This is a center-position rule, not a physical-depth or containment test.

**Depth — Qwen.** Use visible depth and occlusion evidence. Vertical image position alone is insufficient. Allowed answers: `front`, `behind`, `same_depth`.

**Containment — Qwen.** Judge the actual interior of the container:

- `inside`: seated or contained in the interior; protrusion above the opening does not by itself negate containment.
- `outside`: not occupying the interior.
- `partial`: crossing the opening without established settled containment.
- Use `unclear` when interior/support cannot be inferred. Box overlap alone is insufficient.

All relation subtypes use exact answer matching. Report left/right, above/below, depth and containment separately as well as the aggregate spatial curve.

## States and scoring

Qwen returns an observation after identifying the object. Missing, ambiguous or unclear identity cannot yield confirmed attribute/relation success. The [response schema and parser behavior](engineering.md#structured-qwen-responses) are specified separately.

| Observation/result | Score | Aggregation |
|---|---:|---|
| `ok` and exact reference match → `correct` | 1 | Included |
| `ok` and valid nonmatching answer → `incorrect` | 0 | Included |
| `missing` | 0 | Included; missing frequency retained |
| `ambiguous` | 0 | Included; uncertainty frequency retained |
| `unclear` | 0 | Included; uncertainty frequency retained |
| Invalid JSON/category/status combination or execution failure → `evaluation_error` | No score | Excluded from means; error count and denominator retained |

Reported metrics:

1. **Confirmed semantic success:** mean score over valid records; not true generator accuracy.
2. **Paired change:** mean `(intervention score - baseline score)` over valid matched pairs. The generic summary returns score units; multiply by 100 for percentage points.
3. **Uncertain rate:** fraction of valid records marked ambiguous or unclear. Missing rate is also retained in CSV/JSON. Zero uncertainty is not evidence of reliable perception, especially for non-abstaining DINO tasks.
4. **Baseline-correct retention:** success among valid pairs whose baseline score is one, with its denominator.
5. **Count deviation and numeric coverage**, plus texture/spatial subtype curves.

All images remain represented in the saved results. Difficult prompts are not dropped to improve curves. The generic summary reports descriptive means, not confidence intervals. Replicate seeds, clustered scene templates and pairing design are the responsibility of each experiment. The standalone package does not require STAR scale curves.
