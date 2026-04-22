# XiaoxiaoNiu
Computer vision approach to solve TikTok game "XiaoxiaoNiu"

## Usage

```bash
uv sync
uv run python Backend/xiaoxiaoniu_solver.py Backend/data/1.jpeg
uv run uvicorn Backend.api:app --reload
cd Frontend
npm install
npm run dev
```

## React Frontend

The React client lives in `Frontend/` and is designed for the overlay workflow:

- upload a screenshot
- send it to `POST /api/solve`
- preview the original screenshot
- place animated cow markers using normalized coordinates from the backend

Frontend notes:

- Vite dev server runs on `http://127.0.0.1:5173`
- backend requests proxy to `http://127.0.0.1:8000` in development
- set `VITE_API_BASE_URL` if you want to call a different backend directly

FastAPI endpoints:

- `GET /healthz`: health check.
- `POST /api/solve`: upload a screenshot with multipart field name `file`, returns frontend-ready overlay data.

Core entrypoint:

- `XiaoxiaoNiuCowFinder.solve_image_async(image_path)`: async parse a screenshot and return all cow positions.
- `XiaoxiaoNiuCowFinder.solve_image_bytes_async(image_bytes)`: async parse uploaded image bytes and return all cow positions.
- `XiaoxiaoNiuCowFinder.solve_grid_async(color_grid)`: async solve directly from a square 2D color-id array.
- `XiaoxiaoNiuCowFinder.solve_image(image_path)`: parse a screenshot and return all cow positions.
- `XiaoxiaoNiuCowFinder.solve_image_bytes(image_bytes)`: parse uploaded image bytes and return all cow positions.
- `XiaoxiaoNiuCowFinder.solve_grid(color_grid)`: solve directly from a square 2D color-id array.

Main exception base class:

- `XiaoxiaoNiuError`: catch this in application code to handle image loading, board detection/parsing, invalid board, and no-solution failures.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/solve \
  -F "file=@Backend/data/1.jpeg"
```

Response data model for frontend:

- `ok`: whether the request succeeded.
- `data.image.size_px`: original uploaded image width and height.
- `data.board.bounding_box_px`: board rectangle in original image pixels.
- `data.board.bounding_box_normalized`: board rectangle normalized to the original image size.
- `data.board.cows[].center_px`: cow center in original image pixels.
- `data.board.cows[].center_normalized`: cow center normalized to the original image size.
- `data.board.cows[].row` / `col`: one-based board coordinates, useful for textual labels.
- `data.board.cows[].row_index` / `col_index`: zero-based board coordinates, useful for array indexing.
- `data.debug.color_grid` / `region_grid`: optional debug data for development.

Example success payload:

```json
{
  "ok": true,
  "data": {
    "image": {
      "filename": "1.jpeg",
      "size_px": { "width": 896, "height": 1792 }
    },
    "board": {
      "grid_size": 6,
      "bounding_box_px": { "x": 99.0, "y": 658.17, "width": 730.0, "height": 730.0 },
      "bounding_box_normalized": { "x": 0.110491, "y": 0.367282, "width": 0.814732, "height": 0.407366 },
      "cell_size_px": 112.0,
      "cows": [
        {
          "index": 0,
          "row_index": 0,
          "col_index": 2,
          "row": 1,
          "col": 3,
          "center_px": { "x": 401.88, "y": 714.17 },
          "center_normalized": { "x": 0.448527, "y": 0.398533 }
        }
      ]
    },
    "debug": {
      "color_grid": [[0, 0, 1, 2, 2, 2]],
      "region_grid": [[0, 0, 1, 2, 2, 2]]
    }
  }
}
```
