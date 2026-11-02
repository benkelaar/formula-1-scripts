# 003 — Add first-points-year tie-breaker

## Objective

Make cumulative rankings more historically meaningful when drivers have equal
fictional points and identical championship tie-break values.

## Ranking and output changes

After cumulative points, championship count, and first championship year,
order tied drivers by ascending year in which they first earned fictional
points. Use ascending `driverId` only when all earlier values remain equal.

Record `first_points_year` on every ranking row. It is the earliest processed
season in which the driver received a positive fictional-points award. Because
only scoring drivers appear in ranking snapshots, this value is never null.
Increase the ranking output schema version to 2 for the new row field.

## Acceptance criteria

- An earlier first-points year wins an otherwise equal tie.
- `driverId` still produces deterministic ordering when first-points years are
  also equal.
- Existing scoring, cumulative ranking, validation, and atomic output behavior
  remains unchanged.

