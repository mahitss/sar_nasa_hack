"""Parameterized water-candidate screen for synthetic and later experiments.

The functions compare linear gamma0 power. They do not read satellite files,
resample rasters, or assign a confidence score. A result of 1 means the pixel
met the supplied rules. It does not mean the pixel is water.
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
    """

    hh_max_linear: float
    hv_max_linear: float
    min_looks: float
    min_patch_pixels: int
    max_hv_over_hh: float | None = None

    def __post_init__(self) -> None:
        if self.hh_max_linear <= 0 or self.hv_max_linear <= 0:
            raise ValueError("power limits must be positive linear gamma0")
        if self.min_looks < 0:
            raise ValueError("min_looks must be zero or positive")
        if self.min_patch_pixels < 1:
            raise ValueError("min_patch_pixels must be at least 1")
        if self.max_hv_over_hh is not None and self.max_hv_over_hh <= 0:
            raise ValueError("max_hv_over_hh must be positive when set")


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


def screen(
    hhhh: Grid,
    hvhv: Grid,
    looks: Grid,
    gcov_mask: Mask,
    parameters: CandidateParameters,
    gslc_mask: Mask | None = None,
) -> LabelGrid:
    """Label each pixel as invalid (-1), valid non-candidate (0), or candidate (1).

    A same-grid GSLC validity mask may be supplied for a fixture whose grid
    already matches the GCOV arrays. This function does not resample.
    """

    rows, cols = _require_same_shape(hhhh, hvhv, looks, gcov_mask)
    if gslc_mask is not None:
        _require_same_shape(hhhh, gslc_mask)
    raw = [[0 for _ in range(cols)] for _ in range(rows)]
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
                continue
            hh = float(hhhh[row][col])
            hv = float(hvhv[row][col])
            if hh > parameters.hh_max_linear or hv > parameters.hv_max_linear:
                continue
            if parameters.max_hv_over_hh is not None and hv / hh > parameters.max_hv_over_hh:
                continue
            raw[row][col] = 1
    return _remove_small_patches(raw, parameters.min_patch_pixels)


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
) -> LabelGrid:
    """Count how many parameter sets select each pixel.

    The count is an algorithmic sensitivity tally. It is not a probability
    and it is not a confidence percentage.
    """

    if not parameter_sets:
        raise ValueError("at least one parameter set is required")
    total: LabelGrid | None = None
    for parameters in parameter_sets:
        labels = screen(hhhh, hvhv, looks, gcov_mask, parameters, gslc_mask)
        if total is None:
            total = [[0 if value < 0 else 0 for value in row] for row in labels]
            selected = total
        else:
            selected = total
        for row, label_row in enumerate(labels):
            for col, value in enumerate(label_row):
                if value == 1:
                    selected[row][col] += 1
    assert total is not None
    return total


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
    if not math.isfinite(looks) or looks < min_looks:
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
