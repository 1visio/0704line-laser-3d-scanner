# Auto ROI V1 failure audit｜Session01

## Audit boundary

This audit is geometry/provenance-only. It does not use `height_shadow.csv`,
nominal truth height, C0/C1 reconstruction, Session Ground, Base/H1/H-B2
results, residuals, q1/q2, or A-13B outcome to judge or select an ROI.

The immutable Session01 Frozen Steger cache is the only centerline source used
for the audit. It contains 600 frames and 1,672,465 full-sensor `(u,v)` points;
no Steger extraction was rerun.

## Confirmed V1 mechanism

The current Session01 path is:

```text
median centerline u(v)
  -> profile residual against a 61-bin median background
  -> negative/positive step/notch peak candidates
  -> highest score candidate
  -> height ROI = candidate_v +/- fixed 45 px
  -> baseline_before / baseline_after derived from that height range
```

The historical gauge-block evaluator has the same structural issue, with an
additional first-repeat dependency:

```text
first repeat centerline
  -> profile candidate detector
  -> highest-score assignment
  -> height ROI = candidate_v +/- 45 px
```

Evidence in the current code:

- `tools/prepare_session01_roi_freeze.py:603-673` builds a smoothed profile
  residual and detects negative/positive peaks.
- `tools/prepare_session01_roi_freeze.py:658-664` sorts by score and keeps the
  highest-scoring candidates.
- `tools/prepare_session01_roi_freeze.py:676-686` constructs the fixed
  `candidate_v +/-45 px` height range and derives both baselines from it.
- `tools/prepare_session01_roi_freeze.py:1025-1030` selects `candidates[0]`
  without an object-interval identity test.
- `tools/evaluate_daheng_c1_gauge_blocks.py:524-542` detects candidates from
  the first repeat and assigns positions before building the fixed-width ROI.
- `tools/evaluate_daheng_c1_gauge_blocks.py:560-590` repeats the fixed-width
  construction and baseline offsets.

## Failure mechanism

V1 detects a local profile feature, not the complete object interval. A large
or wide response from an image edge, transition, mixed surface, broken line,
or other centerline texture can therefore win the score competition even if
it is not the center of the gauge-block top plateau.

Once that feature is selected, the fixed-width construction propagates the
mistake:

```text
wrong local feature
  -> wrong candidate_v
  -> fixed +/-45 px interval may straddle an edge or mixed surface
  -> both ground baselines are shifted from the actual object boundaries
  -> formal height ROI is not guaranteed to be object-top interior
```

The V1 quality checks do not close this gap:

- `range_is_valid()` only checks image bounds and non-overlap/order.
- formal support checks verify that points exist, not that the centerline is a
  stable object-top plateau.
- `manual_review_required` is a flag, not an algorithmic rejection.
- `annotate_daheng_gauge_rois.py:518-538` validates range geometry only.
- `annotate_daheng_gauge_rois.py:760-767` permits accepting the auto range
  without changing it.
- `prepare_session01_roi_freeze.py:1066` can convert these checks into
  `review_ok`, and `:1151-1156` writes `FROZEN`/`manual_confirmed` from that
  automatic result.

Thus V1 can be syntactically valid, fully supported by centerline points, and
still semantically wrong as a top-interior ROI.

## Development-case observations from the frozen V1 artifacts

These observations are geometry/QC only; no height error was inspected.

| case | V1 height center | V1 height range | formal v median | geometry observation |
|---|---:|---|---:|---|
| `h10_p05` | 1332.5 | `[1288, 1378]` | 1337.0 | largest center-to-formal-median offset (+4.5 px); lower formal support and shorter observed after-baseline support |
| `h20_p03` | 692.5 | `[648, 738]` | 693.0 | range is formally valid, but V1 still provides no object-top plateau/edge identity gate |
| `h30_p04` | 982.5 | `[938, 1028]` | 983.0 | clean-looking reference for point support, but fixed-width semantics remain unverified |
| `h30_p07` | 1902.5 | `[1858, 1948]` | 1900.0 | formal center offset (-2.5 px) and reduced support; not edge-clipped |

All four existing V1 entries were already marked manually confirmed/frozen in
the old registry, and their `manual_roi` matched `auto_roi`. This confirms the
registry state did not independently repair the candidate-center failure mode.

## Required V2 correction

V2 must identify an interval, not a point:

```text
stable ground
  -> first transition / edge (edge1)
  -> stable object-top plateau
  -> second transition / edge (edge2)
  -> stable ground
```

The height ROI must be generated from the interior between the two detected
edges, with explicit transition safety margins and adaptive width. The two
baselines must be selected from stable ground segments outside the respective
edges and may be clipped only at the image boundary, with clipping recorded.

The V2 automatic output must remain a draft: `human_reviewed=false`,
`human_decision=PENDING`, `frozen=false`. No V2 candidate is a formal A-13B
ROI until a human review accepts it.
