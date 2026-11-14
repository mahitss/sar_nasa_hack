"""Parameterized water-candidate screen for synthetic and later experiments.

The functions compare linear gamma0 power. They do not read satellite files,
resample rasters, or assign a confidence score. A result of 1 means the pixel
met the supplied rules. It does not mean the pixel is water.

Mission 005 changes ``sensitivity()`` to return ``SensitivityResult``. The
filtered-candidate count is no longer a bare grid, so an invalid pixel is not
reported as a non-candidate.

This module implements Mission 004 hardening:
- Parameter validation rejects NaN, infinity, zero and negative values.
- screen() retains raw candidate labels before connected-component filtering.
- sensitivity() reports per-pixel validity and candidate stability across
  parameter sets, distinguishing pixels that are invalid in at least one set
  from pixels that are valid in every set.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


class GridMismatch(ValueError):
    """Raised when compared arrays do not share one shape."""


Grid = Sequence[Sequence[float]]
Mask = Sequence[Sequence[int]]
LabelGrid = list[list[int]]


@dataclass(frozen=True)
class CandidateParameters:
    """Rules for one run of the screen.

    Power limits are linear gamma0. They are experiment parameters, not a
    universal NISAR threshold. ``max_hv_over_hh`` may be None to skip the
    cross-polar ratio gate.

    All float parameters must be finite. Power limits and the optional ratio
    gate must be strictly positive. ``min_looks`` must be zero or positive.
    ``min_patch_pixels`` must be at least 1.

    A sample still needs finite ``numberOfLooks`` strictly greater than zero.
    ``min_looks=0`` adds no further floor. It does not make a zero-look sample
    valid.
    """

    hh_max_linear: float
    hv_max_linear: float
    min_looks: float
    min_patch_pixels: int
    max_hv_over_hh: float | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("hh_max_linear", self.hh_max_linear),
            ("hv_max_linear", self.hv_max_linear),
            ("min_looks", self.min_looks),
        ):
            if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
                raise ValueError(f"{name} must be a finite number, got {value!r}")
        if self.hh_max_linear <= 0:
            raise ValueError("hh_max_linear must be a finite positive linear gamma0")
        if self.hv_max_linear <= 0:
            raise ValueError("hv_max_linear must be a finite positive linear gamma0")
        if self.min_looks < 0:
            raise ValueError("min_looks must be zero or positive")
        if not isinstance(self.min_patch_pixels, int) or isinstance(self.min_patch_pixels, bool):
            raise ValueError("min_patch_pixels must be an integer")
        if self.min_patch_pixels < 1:
            raise ValueError("min_patch_pixels must be at least 1")
        if self.max_hv_over_hh is not None:
            if not isinstance(self.max_hv_over_hh, (int, float)) or math.isnan(self.max_hv_over_hh) or math.isinf(self.max_hv_over_hh):
                raise ValueError("max_hv_over_hh must be a finite number when set")
            if self.max_hv_over_hh <= 0:
                raise ValueError("max_hv_over_hh must be positive when set")


@dataclass(frozen=True)
class ScreenResult:
    """Detailed output from one screen run.

    ``raw`` holds the candidate decision before connected-component filtering:
    -1 invalid, 0 valid non-candidate, 1 raw candidate.
    ``filtered`` holds the same classes after small-patch removal.
    ``valid`` holds 0 for invalid pixels and 1 for valid pixels.
    """

    raw: LabelGrid
    filtered: LabelGrid
    valid: LabelGrid


@dataclass(frozen=True)
class SensitivityResult:
    """Per-pixel sensitivity across a collection of parameter sets.

    For every pixel the result records how many parameter sets found it valid,
    how many found it a raw candidate (before patch filtering), and how many
    found it a filtered candidate (after patch filtering).  The total number of
    parameter sets is also recorded so callers can compute stability fractions
    without treating them as probabilities.
    """

    valid_count: LabelGrid
    raw_candidate_count: LabelGrid
    filtered_candidate_count: LabelGrid
    total_sets: int

    def validity_class(self) -> LabelGrid:
        """Classify each pixel by validity across parameter sets.

        Returns a grid of the same shape where each value is:
        - 1: valid in every parameter set
        - 0: valid in at least one but not every parameter set
        - -1: invalid in every parameter set
        """
        rows = len(self.valid_count)
        cols = len(self.valid_count[0])
        out: LabelGrid = [[0 for _ in range(cols)] for _ in range(rows)]
        total = self.total_sets
        for row in range(rows):
            for col in range(cols):
                vc = self.valid_count[row][col]
                if vc == total:
                    out[row][col] = 1
                elif vc > 0:
                    out[row][col] = 0
                else:
                    out[row][col] = -1
        return out

    def candidate_stability_class(self) -> LabelGrid:
        """Classify each pixel by candidate behaviour among valid sets.

        Returns a grid of the same shape where each value is:
        - 1: candidate in every set in which it was valid (and valid in at
          least one set)
        - 0: candidate in some but not all valid sets
        - -1: never a candidate while valid (or invalid in every set)
        """
        rows = len(self.valid_count)
        cols = len(self.valid_count[0])
        out: LabelGrid = [[0 for _ in range(cols)] for _ in range(rows)]
        for row in range(rows):
            for col in range(cols):
                vc = self.valid_count[row][col]
                if vc == 0:
                    out[row][col] = -1
                    continue
                fc = self.filtered_candidate_count[row][col]
                if fc == vc:
                    out[row][col] = 1
                elif fc > 0:
                    out[row][col] = 0
                else:
                    out[row][col] = -1
        return out

    def __getitem__(self, row: int) -> list[int]:
        """Backward-compatible row access: behaves like filtered_candidate_count."""
        return self.filtered_candidate_count[row]

    def __iter__(self):
        """Backward-compatible iteration: yields rows of filtered_candidate_count."""
        return iter(self.filtered_candidate_count)


def linear_to_db(power: float) -> float:
    """Return 10*log10(power) for a finite positive linear power."""

    if not math.isfinite(power) or power <= 0:
        raise ValueError("dB is defined only for finite positive power")
    return 10.0 * math.log10(power)


def db_to_linear(decibels: float) -> float:
    """Return the linear power corresponding to a dB value."""

    if not math.isfinite(decibels):
        raise ValueError("dB value must be finite")
    return 10.0 ** (decibels / 10.0)


def screen_detailed(
    hhhh: Grid,
    hvhv: Grid,
    looks: Grid,
    gcov_mask: Mask,
    parameters: CandidateParameters,
    gslc_mask: Mask | None = None,
) -> ScreenResult:
    """Run one screen and return raw, filtered, and validity labels.

    A same-grid GSLC validity mask may be supplied for a fixture whose grid
    already matches the GCOV arrays. This function does not resample.
    """

    rows, cols = _require_same_shape(hhhh, hvhv, looks, gcov_mask)
    if gslc_mask is not None:
        _require_same_shape(hhhh, gslc_mask)

    raw = [[0 for _ in range(cols)] for _ in range(rows)]
    valid = [[0 for _ in range(cols)] for _ in range(rows)]

    for row in range(rows):
        for col in range(cols):
            if not _valid_sample(
                hhhh[row][col],
                hvhv[row][col],
                looks[row][col],
                int(gcov_mask[row][col]),
                None if gslc_mask is None else int(gslc_mask[row][col]),
                parameters.min_looks,
            ):
                raw[row][col] = -1
                valid[row][col] = 0
                continue
            valid[row][col] = 1
            hh = float(hhhh[row][col])
            hv = float(hvhv[row][col])
            if hh > parameters.hh_max_linear or hv > parameters.hv_max_linear:
                continue
            if parameters.max_hv_over_hh is not None and hv / hh > parameters.max_hv_over_hh:
                continue
            raw[row][col] = 1

    filtered = _remove_small_patches(raw, parameters.min_patch_pixels)
    return ScreenResult(raw=raw, filtered=filtered, valid=valid)


def screen(
    hhhh: Grid,
    hvhv: Grid,
    looks: Grid,
    gcov_mask: Mask,
    parameters: CandidateParameters,
    gslc_mask: Mask | None = None,
) -> LabelGrid:
    """Label each pixel as invalid (-1), valid non-candidate (0), or candidate (1).

    The returned grid is the post-filter (connected-component) labelling.
    Callers needing the pre-filter raw labels should use screen_detailed().
    """

    return screen_detailed(hhhh, hvhv, looks, gcov_mask, parameters, gslc_mask).filtered


def compare(earlier: LabelGrid, later: LabelGrid) -> dict[str, int | LabelGrid]:
    """Compare two screens without treating invalid pixels as change.

    Class codes are 0 excluded, 1 persistent candidate, 2 gained candidate,
    3 lost candidate, and 4 valid on both dates but not a candidate.
    """

    rows, cols = _require_same_shape(earlier, later)
    classes = [[0 for _ in range(cols)] for _ in range(rows)]
    counts = {"persistent": 0, "gained": 0, "lost": 0, "excluded": 0, "stable_non_candidate": 0}
    for row in range(rows):
        for col in range(cols):
            first = earlier[row][col]
            second = later[row][col]
            if first < 0 or second < 0:
                counts["excluded"] += 1
                continue
            if first == 1 and second == 1:
                classes[row][col] = 1
                counts["persistent"] += 1
            elif first == 0 and second == 1:
                classes[row][col] = 2
                counts["gained"] += 1
            elif first == 1 and second == 0:
                classes[row][col] = 3
                counts["lost"] += 1
            else:
                classes[row][col] = 4
                counts["stable_non_candidate"] += 1
    return {"classes": classes, **counts}


def sensitivity(
    hhhh: Grid,
    hvhv: Grid,
    looks: Grid,
    gcov_mask: Mask,
    parameter_sets: Sequence[CandidateParameters],
    gslc_mask: Mask | None = None,
) -> SensitivityResult:
    """Report per-pixel sensitivity across parameter sets.

    For every pixel the result records how many parameter sets found it valid,
    how many found it a raw candidate, and how many found it a filtered
    candidate.  The count is an algorithmic sensitivity tally. It is not a
    probability and it is not a confidence percentage.
    """

    if not parameter_sets:
        raise ValueError("at least one parameter set is required")

    rows, cols = _require_same_shape(hhhh, hvhv, looks, gcov_mask)
    valid_count = [[0 for _ in range(cols)] for _ in range(rows)]
    raw_candidate_count = [[0 for _ in range(cols)] for _ in range(rows)]
    filtered_candidate_count = [[0 for _ in range(cols)] for _ in range(rows)]

    for parameters in parameter_sets:
        result = screen_detailed(hhhh, hvhv, looks, gcov_mask, parameters, gslc_mask)
        for row in range(rows):
            for col in range(cols):
                valid_count[row][col] += result.valid[row][col]
                if result.raw[row][col] == 1:
                    raw_candidate_count[row][col] += 1
                if result.filtered[row][col] == 1:
                    filtered_candidate_count[row][col] += 1

    return SensitivityResult(
        valid_count=valid_count,
        raw_candidate_count=raw_candidate_count,
        filtered_candidate_count=filtered_candidate_count,
        total_sets=len(parameter_sets),
    )


def _valid_sample(
    hh: float,
    hv: float,
    looks: float,
    gcov_code: int,
    gslc_code: int | None,
    min_looks: float,
) -> bool:
    if not _positive_subswath(gcov_code):
        return False
    if gslc_code is not None and not _positive_subswath(gslc_code):
        return False
    if not math.isfinite(hh) or not math.isfinite(hv) or hh <= 0 or hv <= 0:
        return False
    # Zero and negative looks are invalid even when min_looks is 0.
    # min_looks adds a floor; it does not accept a non-positive sample.
    if not math.isfinite(looks) or looks <= 0 or looks < min_looks:
        return False
    return True


def _positive_subswath(code: int) -> bool:
    return code > 0 and code != 255


def _remove_small_patches(labels: LabelGrid, min_pixels: int) -> LabelGrid:
    rows, cols = _require_same_shape(labels)
    seen = [[False for _ in range(cols)] for _ in range(rows)]
    output = [row[:] for row in labels]
    for row in range(rows):
        for col in range(cols):
            if labels[row][col] != 1 or seen[row][col]:
                continue
            component: list[tuple[int, int]] = []
            stack = [(row, col)]
            seen[row][col] = True
            while stack:
                y_coord, x_coord = stack.pop()
                component.append((y_coord, x_coord))
                for y_step, x_step in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    next_y = y_coord + y_step
                    next_x = x_coord + x_step
                    if (
                        0 <= next_y < rows
                        and 0 <= next_x < cols
                        and not seen[next_y][next_x]
                        and labels[next_y][next_x] == 1
                    ):
                        seen[next_y][next_x] = True
                        stack.append((next_y, next_x))
            if len(component) < min_pixels:
                for y_coord, x_coord in component:
                    output[y_coord][x_coord] = 0
    return output


def _require_same_shape(*grids: Grid | Mask | LabelGrid) -> tuple[int, int]:
    if not grids or not grids[0] or not grids[0][0]:
        raise ValueError("grids must be non-empty")
    rows = len(grids[0])
    cols = len(grids[0][0])
    for grid in grids:
        if len(grid) != rows or any(len(row) != cols for row in grid):
            raise GridMismatch("all arrays must share one rectangular shape")
    return rows, cols
