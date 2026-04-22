from __future__ import annotations

import asyncio
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image


Grid = list[list[int]]
Coord = tuple[int, int]


class XiaoxiaoNiuError(Exception):
    """Base exception for all solver failures."""


class ImageLoadError(XiaoxiaoNiuError):
    """Raised when the input image cannot be opened or decoded."""


class BoardDetectionError(XiaoxiaoNiuError):
    """Raised when the board cells cannot be detected from the image."""


class BoardParsingError(XiaoxiaoNiuError):
    """Raised when a detected board cannot be converted into a valid square grid."""


class InvalidBoardError(XiaoxiaoNiuError):
    """Raised when the provided color grid violates puzzle assumptions."""


class NoSolutionError(XiaoxiaoNiuError):
    """Raised when a valid cow placement does not exist for the parsed board."""


@dataclass(frozen=True)
class BoardParseResult:
    image_path: Path
    image_size_px: tuple[int, int]
    grid_size: int
    board_bbox_px: tuple[float, float, float, float]
    cell_size_px: float
    color_grid: Grid
    region_grid: Grid
    cows_zero_based: list[Coord]
    cows_one_based: list[Coord]
    cow_centers_px: list[tuple[float, float]]
    cell_centers_px: list[list[tuple[float, float]]]


class XiaoxiaoNiuCowFinder:
    """Parse the puzzle board from an image and solve all cow positions."""

    def __init__(
        self,
        saturation_threshold: float = 0.25,
        min_component_area: int = 10_000,
        min_cell_side: int = 90,
        max_cell_side: int = 130,
        color_distance_threshold: float = 32.0,
    ) -> None:
        self.saturation_threshold = saturation_threshold
        self.min_component_area = min_component_area
        self.min_cell_side = min_cell_side
        self.max_cell_side = max_cell_side
        self.color_distance_threshold = color_distance_threshold

    async def solve_image_async(self, image_path: str | Path) -> BoardParseResult:
        return await asyncio.to_thread(self._solve_image_sync, Path(image_path))

    def solve_image(self, image_path: str | Path) -> BoardParseResult:
        return self._solve_image_sync(Path(image_path))

    async def solve_image_bytes_async(
        self, image_bytes: bytes, source_name: str = "<uploaded-image>"
    ) -> BoardParseResult:
        return await asyncio.to_thread(self._solve_image_bytes_sync, image_bytes, source_name)

    def solve_image_bytes(
        self, image_bytes: bytes, source_name: str = "<uploaded-image>"
    ) -> BoardParseResult:
        return self._solve_image_bytes_sync(image_bytes, source_name)

    async def solve_grid_async(self, color_grid: Sequence[Sequence[int]]) -> list[Coord]:
        normalized_grid = self._normalize_grid(color_grid)
        return await asyncio.to_thread(self._solve_grid_sync, normalized_grid)

    def solve_grid(self, color_grid: Sequence[Sequence[int]]) -> list[Coord]:
        return self._solve_grid_sync(self._normalize_grid(color_grid))

    def _solve_image_sync(self, image_path: Path) -> BoardParseResult:
        try:
            image_rgb = self._load_image_array_from_path(Path(image_path))
        except Exception as exc:
            raise ImageLoadError(f"Failed to open image: {image_path}") from exc

        return self._solve_image_array(image_rgb, Path(image_path))

    def _solve_image_bytes_sync(
        self, image_bytes: bytes, source_name: str = "<uploaded-image>"
    ) -> BoardParseResult:
        try:
            image_rgb = self._load_image_array_from_bytes(image_bytes)
        except Exception as exc:
            raise ImageLoadError(f"Failed to decode image bytes: {source_name}") from exc

        return self._solve_image_array(image_rgb, Path(source_name))

    def _solve_image_array(self, image_rgb: np.ndarray, source_path: Path) -> BoardParseResult:
        image_height, image_width = image_rgb.shape[:2]
        boxes = self._find_colored_cell_candidates(image_rgb)
        if not boxes:
            raise BoardDetectionError("No candidate board cells were detected in the image.")

        x_centers, y_centers, cell_side = self._infer_grid_centers(boxes)
        board_bbox = self._build_board_bbox(x_centers, y_centers, cell_side)
        cell_centers = [[(x, y) for x in x_centers] for y in y_centers]
        sampled_colors = self._sample_cell_colors(image_rgb, x_centers, y_centers, cell_side)
        color_grid = self._quantize_color_grid(sampled_colors)
        cows = self.solve_grid(color_grid)

        return BoardParseResult(
            image_path=source_path,
            image_size_px=(image_width, image_height),
            grid_size=len(color_grid),
            board_bbox_px=board_bbox,
            cell_size_px=float(cell_side),
            color_grid=color_grid,
            region_grid=self._build_region_grid(color_grid),
            cows_zero_based=cows,
            cows_one_based=[(row + 1, col + 1) for row, col in cows],
            cow_centers_px=[cell_centers[row][col] for row, col in cows],
            cell_centers_px=cell_centers,
        )

    def _solve_grid_sync(self, grid: Sequence[Sequence[int]]) -> list[Coord]:
        n = len(grid)
        regions = self._build_region_grid(grid)
        region_count = len({cell for row in regions for cell in row})

        if region_count != n:
            raise InvalidBoardError(
                f"Expected exactly {n} connected color regions on an {n}x{n} board, "
                f"but detected {region_count} regions."
            )

        cells_by_region: dict[int, list[Coord]] = {}
        for row in range(n):
            for col in range(n):
                cells_by_region.setdefault(regions[row][col], []).append((row, col))

        row_candidates: list[list[Coord]] = []
        for row in range(n):
            ordered = sorted(
                ((row, col) for col in range(n)),
                key=lambda coord: (len(cells_by_region[regions[coord[0]][coord[1]]]), coord[1]),
            )
            row_candidates.append(ordered)

        solution: list[Coord] = []
        used_cols: set[int] = set()
        used_regions: set[int] = set()

        suffix_region_union: list[set[int]] = [set() for _ in range(n + 1)]
        for row in range(n - 1, -1, -1):
            suffix_region_union[row] = suffix_region_union[row + 1] | {
                regions[row][col] for col in range(n)
            }

        def backtrack(row: int) -> bool:
            if row == n:
                return True

            remaining_rows = n - row
            remaining_cols = n - len(used_cols)
            remaining_regions = region_count - len(used_regions)
            if remaining_cols < remaining_rows or remaining_regions < remaining_rows:
                return False

            future_regions = suffix_region_union[row] - used_regions
            if len(future_regions) < remaining_rows:
                return False

            prev_col = solution[-1][1] if solution else None

            for candidate_row, candidate_col in row_candidates[row]:
                region_id = regions[candidate_row][candidate_col]
                if candidate_col in used_cols or region_id in used_regions:
                    continue
                if prev_col is not None and abs(candidate_col - prev_col) <= 1:
                    continue

                solution.append((candidate_row, candidate_col))
                used_cols.add(candidate_col)
                used_regions.add(region_id)

                if backtrack(row + 1):
                    return True

                solution.pop()
                used_cols.remove(candidate_col)
                used_regions.remove(region_id)

            return False

        if not backtrack(0):
            raise NoSolutionError("No valid cow placement exists for the detected board.")

        return solution

    def _find_colored_cell_candidates(
        self, image_rgb: np.ndarray
    ) -> list[tuple[int, int, int, int, float, float, int]]:
        rgb = image_rgb.astype(np.float32) / 255.0
        channel_max = rgb.max(axis=2)
        channel_min = rgb.min(axis=2)
        saturation = np.where(channel_max == 0.0, 0.0, (channel_max - channel_min) / channel_max)
        mask = saturation >= self.saturation_threshold

        height, width = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        boxes: list[tuple[int, int, int, int, float, float, int]] = []

        for row in range(height):
            cols = np.flatnonzero(mask[row] & ~visited[row])
            for col in cols:
                stack = [(row, col)]
                visited[row, col] = True
                min_row = max_row = row
                min_col = max_col = col
                area = 0

                while stack:
                    cur_row, cur_col = stack.pop()
                    area += 1
                    if cur_row < min_row:
                        min_row = cur_row
                    if cur_row > max_row:
                        max_row = cur_row
                    if cur_col < min_col:
                        min_col = cur_col
                    if cur_col > max_col:
                        max_col = cur_col

                    for next_row, next_col in (
                        (cur_row - 1, cur_col),
                        (cur_row + 1, cur_col),
                        (cur_row, cur_col - 1),
                        (cur_row, cur_col + 1),
                    ):
                        if (
                            0 <= next_row < height
                            and 0 <= next_col < width
                            and mask[next_row, next_col]
                            and not visited[next_row, next_col]
                        ):
                            visited[next_row, next_col] = True
                            stack.append((next_row, next_col))

                box_width = max_col - min_col + 1
                box_height = max_row - min_row + 1
                if (
                    area >= self.min_component_area
                    and self.min_cell_side <= box_width <= self.max_cell_side
                    and self.min_cell_side <= box_height <= self.max_cell_side
                    and abs(box_width - box_height) <= 5
                ):
                    boxes.append(
                        (
                            min_col,
                            min_row,
                            max_col + 1,
                            max_row + 1,
                            (min_col + max_col + 1) / 2.0,
                            (min_row + max_row + 1) / 2.0,
                            int(round((box_width + box_height) / 2)),
                        )
                    )

        return boxes

    def _infer_grid_centers(
        self, boxes: Sequence[tuple[int, int, int, int, float, float, int]]
    ) -> tuple[list[float], list[float], int]:
        cell_side = int(round(float(np.median([box[6] for box in boxes]))))
        merge_threshold = cell_side * 0.6

        x_groups = self._cluster_1d([box[4] for box in boxes], merge_threshold)
        y_groups = self._cluster_1d([box[5] for box in boxes], merge_threshold)

        x_centers = [self._mean(group) for group in x_groups if len(group) >= 2]
        y_centers = [self._mean(group) for group in y_groups if len(group) >= 2]

        if len(x_centers) != len(y_centers):
            raise BoardParsingError(
                "Detected row/column counts do not match. "
                f"rows={len(y_centers)}, cols={len(x_centers)}"
            )
        if not x_centers or len(x_centers) < 2:
            raise BoardParsingError("Failed to infer a valid square board from the image.")

        return x_centers, y_centers, cell_side

    def _sample_cell_colors(
        self,
        image_rgb: np.ndarray,
        x_centers: Sequence[float],
        y_centers: Sequence[float],
        cell_side: int,
    ) -> list[list[np.ndarray]]:
        patch_radius = max(4, int(round(cell_side * 0.18)))
        height, width, _ = image_rgb.shape
        sampled_rows: list[list[np.ndarray]] = []

        for center_y in y_centers:
            sampled_row: list[np.ndarray] = []
            for center_x in x_centers:
                x = int(round(center_x))
                y = int(round(center_y))
                left = max(0, x - patch_radius)
                right = min(width, x + patch_radius + 1)
                top = max(0, y - patch_radius)
                bottom = min(height, y + patch_radius + 1)
                patch = image_rgb[top:bottom, left:right]
                sampled_row.append(patch.mean(axis=(0, 1)))
            sampled_rows.append(sampled_row)

        return sampled_rows

    def _quantize_color_grid(self, sampled_colors: Sequence[Sequence[np.ndarray]]) -> Grid:
        flat_colors = [np.asarray(color, dtype=np.float32) for row in sampled_colors for color in row]
        palette: list[np.ndarray] = []
        counts: list[int] = []
        assignments: list[int] = []

        for color in flat_colors:
            if not palette:
                palette.append(color.copy())
                counts.append(1)
                assignments.append(0)
                continue

            distances = [float(np.linalg.norm(color - base)) for base in palette]
            best_index = int(np.argmin(distances))
            if distances[best_index] <= self.color_distance_threshold:
                current_count = counts[best_index]
                palette[best_index] = (palette[best_index] * current_count + color) / (current_count + 1)
                counts[best_index] = current_count + 1
                assignments.append(best_index)
            else:
                palette.append(color.copy())
                counts.append(1)
                assignments.append(len(palette) - 1)

        row_length = len(sampled_colors[0])
        return [
            assignments[index : index + row_length]
            for index in range(0, len(assignments), row_length)
        ]

    def _build_region_grid(self, color_grid: Sequence[Sequence[int]]) -> Grid:
        grid = self._normalize_grid(color_grid)
        n = len(grid)
        regions = [[-1] * n for _ in range(n)]
        region_id = 0

        for row in range(n):
            for col in range(n):
                if regions[row][col] != -1:
                    continue

                color_id = grid[row][col]
                stack = [(row, col)]
                regions[row][col] = region_id

                while stack:
                    cur_row, cur_col = stack.pop()
                    for next_row, next_col in self._neighbors8(cur_row, cur_col, n):
                        if regions[next_row][next_col] == -1 and grid[next_row][next_col] == color_id:
                            regions[next_row][next_col] = region_id
                            stack.append((next_row, next_col))

                region_id += 1

        return regions

    def _normalize_grid(self, color_grid: Sequence[Sequence[int]]) -> Grid:
        grid = [list(map(int, row)) for row in color_grid]
        if not grid:
            raise InvalidBoardError("The input grid cannot be empty.")
        size = len(grid)
        if any(len(row) != size for row in grid):
            raise InvalidBoardError("The puzzle board must be a non-empty square grid.")
        return grid

    def _cluster_1d(self, values: Iterable[float], threshold: float) -> list[list[float]]:
        sorted_values = sorted(float(value) for value in values)
        if not sorted_values:
            return []

        groups: list[list[float]] = [[sorted_values[0]]]
        for value in sorted_values[1:]:
            current_group = groups[-1]
            if abs(value - self._mean(current_group)) <= threshold:
                current_group.append(value)
            else:
                groups.append([value])
        return groups

    @staticmethod
    def _neighbors8(row: int, col: int, size: int) -> Iterable[Coord]:
        for row_delta in (-1, 0, 1):
            for col_delta in (-1, 0, 1):
                if row_delta == 0 and col_delta == 0:
                    continue
                next_row = row + row_delta
                next_col = col + col_delta
                if 0 <= next_row < size and 0 <= next_col < size:
                    yield next_row, next_col

    @staticmethod
    def _mean(values: Sequence[float]) -> float:
        return sum(values) / len(values)

    @staticmethod
    def _load_image_array_from_path(image_path: Path) -> np.ndarray:
        return np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)

    @staticmethod
    def _load_image_array_from_bytes(image_bytes: bytes) -> np.ndarray:
        return np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"), dtype=np.uint8)

    @staticmethod
    def _build_board_bbox(
        x_centers: Sequence[float], y_centers: Sequence[float], cell_side: int
    ) -> tuple[float, float, float, float]:
        half_side = cell_side / 2.0
        left = min(x_centers) - half_side
        top = min(y_centers) - half_side
        right = max(x_centers) + half_side
        bottom = max(y_centers) + half_side
        return (left, top, right - left, bottom - top)


def _to_jsonable(result: BoardParseResult) -> dict[str, object]:
    return {
        "image_path": str(result.image_path),
        "image_size_px": list(result.image_size_px),
        "grid_size": result.grid_size,
        "board_bbox_px": [round(value, 2) for value in result.board_bbox_px],
        "cell_size_px": round(result.cell_size_px, 2),
        "color_grid": result.color_grid,
        "region_grid": result.region_grid,
        "cows_zero_based": result.cows_zero_based,
        "cows_one_based": result.cows_one_based,
        "cow_centers_px": [(round(x, 2), round(y, 2)) for x, y in result.cow_centers_px],
        "cell_centers_px": [[(round(x, 2), round(y, 2)) for x, y in row] for row in result.cell_centers_px],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Solve XiaoxiaoNiu puzzle screenshots.")
    parser.add_argument("image", type=Path, help="Path to the puzzle screenshot.")
    args = parser.parse_args()

    async def _main() -> None:
        solver = XiaoxiaoNiuCowFinder()
        solved = await solver.solve_image_async(args.image)
        print(json.dumps(_to_jsonable(solved), ensure_ascii=False, indent=2))

    asyncio.run(_main())
