from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from threading import Lock
from typing import Literal

import httpx
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from Backend.xiaoxiaoniu_solver import (
    BoardDetectionError,
    BoardParseResult,
    BoardParsingError,
    ImageLoadError,
    InvalidBoardError,
    NoSolutionError,
    XiaoxiaoNiuCowFinder,
)


ErrorType = Literal[
    "image_load_error",
    "board_detection_error",
    "board_parsing_error",
    "invalid_board_error",
    "no_solution_error",
]


class PointModel(BaseModel):
    x: float
    y: float


class SizeModel(BaseModel):
    width: int
    height: int


class RectModel(BaseModel):
    x: float
    y: float
    width: float
    height: float


class CowPositionModel(BaseModel):
    index: int = Field(..., description="Zero-based index in the solved cow list.")
    row_index: int = Field(..., description="Zero-based row index.")
    col_index: int = Field(..., description="Zero-based column index.")
    row: int = Field(..., description="One-based row index.")
    col: int = Field(..., description="One-based column index.")
    center_px: PointModel
    center_normalized: PointModel = Field(
        ..., description="Position normalized to the original image size, in [0, 1]."
    )


class ImageMetaModel(BaseModel):
    filename: str
    size_px: SizeModel


class BoardOverlayModel(BaseModel):
    grid_size: int
    bounding_box_px: RectModel
    bounding_box_normalized: RectModel
    cell_size_px: float
    cows: list[CowPositionModel]


class DebugBoardModel(BaseModel):
    color_grid: list[list[int]]
    region_grid: list[list[int]]


class SolveDataModel(BaseModel):
    image: ImageMetaModel
    board: BoardOverlayModel
    debug: DebugBoardModel


class SolveSuccessResponse(BaseModel):
    ok: Literal[True] = True
    data: SolveDataModel


class ErrorDetailModel(BaseModel):
    type: ErrorType
    message: str


class SolveErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ErrorDetailModel


class VisitCounterDataModel(BaseModel):
    total_visits: int


class VisitCounterResponse(BaseModel):
    ok: Literal[True] = True
    data: VisitCounterDataModel


class VisitCounterStore:
    async def read_total(self) -> int:
        raise NotImplementedError

    async def increment(self) -> int:
        raise NotImplementedError


class FileVisitCounterStore(VisitCounterStore):
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._lock = Lock()

    async def read_total(self) -> int:
        return await asyncio.to_thread(self._read_total_sync)

    async def increment(self) -> int:
        return await asyncio.to_thread(self._increment_sync)

    def _read_total_sync(self) -> int:
        with self._lock:
            return self._read_payload()["total_visits"]

    def _increment_sync(self) -> int:
        with self._lock:
            payload = self._read_payload()
            payload["total_visits"] += 1
            self._write_payload(payload)
            return payload["total_visits"]

    def _read_payload(self) -> dict[str, int]:
        if not self.file_path.exists():
            return {"total_visits": 0}

        try:
            payload = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"total_visits": 0}

        total_visits = payload.get("total_visits", 0)
        if not isinstance(total_visits, int) or total_visits < 0:
            total_visits = 0
        return {"total_visits": total_visits}

    def _write_payload(self, payload: dict[str, int]) -> None:
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


class RedisVisitCounterStore(VisitCounterStore):
    def __init__(self, rest_url: str, rest_token: str, key: str = "site_visits") -> None:
        self.rest_url = rest_url.rstrip("/")
        self.rest_token = rest_token
        self.key = key

    async def read_total(self) -> int:
        payload = await self._request("GET", f"/get/{self.key}")
        return self._coerce_result(payload.get("result"))

    async def increment(self) -> int:
        payload = await self._request("POST", f"/incr/{self.key}")
        return self._coerce_result(payload.get("result"))

    async def _request(self, method: str, path: str) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.request(
                method,
                f"{self.rest_url}{path}",
                headers={"Authorization": f"Bearer {self.rest_token}"},
            )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(str(payload["error"]))
        return payload

    @staticmethod
    def _coerce_result(value: object) -> int:
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0


def _build_visit_counter_store() -> VisitCounterStore:
    rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    key = os.getenv("SITE_VISITS_KEY", "site_visits")

    if rest_url and rest_token:
        return RedisVisitCounterStore(rest_url=rest_url, rest_token=rest_token, key=key)

    return FileVisitCounterStore(Path(__file__).with_name("page_metrics.json"))


app = FastAPI(title="XiaoxiaoNiu API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

solver = XiaoxiaoNiuCowFinder()
counter_store = _build_visit_counter_store()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/site-visits", response_model=VisitCounterResponse)
async def get_site_visits() -> VisitCounterResponse:
    return VisitCounterResponse(data=VisitCounterDataModel(total_visits=await counter_store.read_total()))


@app.post("/api/site-visits", response_model=VisitCounterResponse)
async def register_site_visit() -> VisitCounterResponse:
    return VisitCounterResponse(data=VisitCounterDataModel(total_visits=await counter_store.increment()))


@app.post(
    "/api/solve",
    response_model=SolveSuccessResponse,
    responses={
        400: {"model": SolveErrorResponse},
        422: {"description": "Invalid upload payload."},
    },
)
async def solve_screenshot(file: UploadFile = File(...)) -> SolveSuccessResponse | JSONResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        return _error_response("image_load_error", "Uploaded file must be an image.")

    image_bytes = await file.read()
    if not image_bytes:
        return _error_response("image_load_error", "Uploaded image is empty.")

    try:
        result = await solver.solve_image_bytes_async(image_bytes, source_name=file.filename or "<upload>")
    except ImageLoadError as exc:
        return _error_response("image_load_error", str(exc))
    except BoardDetectionError as exc:
        return _error_response("board_detection_error", str(exc))
    except BoardParsingError as exc:
        return _error_response("board_parsing_error", str(exc))
    except InvalidBoardError as exc:
        return _error_response("invalid_board_error", str(exc))
    except NoSolutionError as exc:
        return _error_response("no_solution_error", str(exc))

    return _to_response(result)


def _to_response(result: BoardParseResult) -> SolveSuccessResponse:
    image_width, image_height = result.image_size_px
    board_x, board_y, board_width, board_height = result.board_bbox_px

    cows = [
        CowPositionModel(
            index=index,
            row_index=row_index,
            col_index=col_index,
            row=row_index + 1,
            col=col_index + 1,
            center_px=PointModel(x=round(center_x, 2), y=round(center_y, 2)),
            center_normalized=PointModel(
                x=round(center_x / image_width, 6),
                y=round(center_y / image_height, 6),
            ),
        )
        for index, ((row_index, col_index), (center_x, center_y)) in enumerate(
            zip(result.cows_zero_based, result.cow_centers_px, strict=True)
        )
    ]

    return SolveSuccessResponse(
        data=SolveDataModel(
            image=ImageMetaModel(
                filename=result.image_path.name,
                size_px=SizeModel(width=image_width, height=image_height),
            ),
            board=BoardOverlayModel(
                grid_size=result.grid_size,
                bounding_box_px=RectModel(
                    x=round(board_x, 2),
                    y=round(board_y, 2),
                    width=round(board_width, 2),
                    height=round(board_height, 2),
                ),
                bounding_box_normalized=RectModel(
                    x=round(board_x / image_width, 6),
                    y=round(board_y / image_height, 6),
                    width=round(board_width / image_width, 6),
                    height=round(board_height / image_height, 6),
                ),
                cell_size_px=round(result.cell_size_px, 2),
                cows=cows,
            ),
            debug=DebugBoardModel(
                color_grid=result.color_grid,
                region_grid=result.region_grid,
            ),
        )
    )


def _error_response(error_type: ErrorType, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "ok": False,
            "error": {
                "type": error_type,
                "message": message,
            },
        },
    )
