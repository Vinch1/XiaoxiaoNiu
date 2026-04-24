import { startTransition, useEffect, useRef, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const initialStatus = {
  kind: "idle",
  message: "Upload a screenshot to reveal the hidden cows.",
};

const COW_DROP_STAGGER_MS = 120;
const COW_DROP_VARIATION_MS = 24;

function App() {
  const [visitCount, setVisitCount] = useState(null);
  const [visitCountFlash, setVisitCountFlash] = useState(false);
  const [status, setStatus] = useState(initialStatus);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef(null);
  const previousVisitCountRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    let pollTimerId;
    let animationTimerId;

    async function syncVisitCount(method) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/site-visits`, {
          method,
        });
        if (!response.ok) {
          throw new Error("Visit counter request failed.");
        }
        const payload = await response.json();
        const nextCount = payload?.data?.total_visits ?? null;
        if (isMounted) {
          if (
            typeof nextCount === "number" &&
            typeof previousVisitCountRef.current === "number" &&
            nextCount > previousVisitCountRef.current
          ) {
            setVisitCountFlash(true);
            window.clearTimeout(animationTimerId);
            animationTimerId = window.setTimeout(() => {
              setVisitCountFlash(false);
            }, 900);
          }
          previousVisitCountRef.current = nextCount;
          setVisitCount(nextCount);
        }
      } catch {
        if (isMounted) {
          setVisitCount(null);
        }
      }
    }

    async function registerInitialVisit() {
      const sessionKey = "xiaoxiaoniu-visit-registered";
      const hasTrackedInSession = window.sessionStorage.getItem(sessionKey) === "1";
      if (!hasTrackedInSession) {
        window.sessionStorage.setItem(sessionKey, "1");
      }
      await syncVisitCount(hasTrackedInSession ? "GET" : "POST");
    }

    registerInitialVisit();
    pollTimerId = window.setInterval(() => {
      syncVisitCount("GET");
    }, 10_000);

    return () => {
      isMounted = false;
      window.clearInterval(pollTimerId);
      window.clearTimeout(animationTimerId);
    };
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [selectedFile]);

  async function handleFileChange(event) {
    const [file] = event.target.files ?? [];
    if (!file) {
      return;
    }

    startTransition(() => {
      setSelectedFile(file);
      setResult(null);
        setStatus({
          kind: "ready",
          message: `${file.name} is ready. Click "Reveal All Cows" to solve.`,
        });
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!selectedFile) {
      setStatus({
        kind: "error",
        message: "Pick a screenshot first.",
      });
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    setIsSubmitting(true);
    setStatus({
      kind: "loading",
      message: "Reading the board and finding the hidden cows...",
    });

    try {
      const response = await fetch(`${API_BASE_URL}/api/solve`, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        throw new Error(payload?.error?.message ?? "The backend could not solve this screenshot.");
      }

      startTransition(() => {
        setResult(payload.data);
        setStatus({
          kind: "success",
          message: `${payload.data.board.cows.length} hidden cows have been revealed.`,
        });
      });
    } catch (error) {
      startTransition(() => {
        setResult(null);
        setStatus({
          kind: "error",
          message: error instanceof Error ? error.message : "Unexpected request failure.",
        });
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  function triggerFilePicker() {
    inputRef.current?.click();
  }

  const cows = result?.board.cows ?? [];

  return (
    <div className="app-shell">
      <header className="hero-panel">
        <div className="hero-copy reveal reveal-1">
          <div className="brand-row">
            <div className="brand-mark" aria-hidden="true">🐮</div>
            <div className="brand-copy">
              <p className="eyebrow">XiaoxiaoNiu</p>
              <strong>Cow Finder</strong>
            </div>
            <div className="hero-status-wrap">
              <VisitCounter count={visitCount} isAnimated={visitCountFlash} />
            </div>
          </div>
          <h1>Find every hidden cow.</h1>
          <p className="hero-text">
            Upload a XiaoxiaoNiu screenshot and instantly reveal all hidden cow positions on the board.
          </p>
        </div>
      </header>

      <main className="workspace">
        <section className="control-panel reveal reveal-2">
          <div className="panel-header">
            <p className="panel-kicker">Upload</p>
            <h2>Upload Screenshot</h2>
          </div>

          <form className="uploader" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              className="visually-hidden"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
            />

            <button className="dropzone" type="button" onClick={triggerFilePicker}>
              <span className="dropzone-icon">📤</span>
              <span className="dropzone-label">
                {selectedFile ? selectedFile.name : "Upload a screenshot"}
              </span>
              <span className="dropzone-hint">Supports PNG, JPG</span>
            </button>

            <div className="action-row">
              <button className="primary-button" type="submit" disabled={!selectedFile || isSubmitting}>
                {isSubmitting ? "Revealing..." : "Reveal All Cows"}
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  startTransition(() => {
                    setSelectedFile(null);
                    setResult(null);
                    setStatus(initialStatus);
                  });
                  if (inputRef.current) {
                    inputRef.current.value = "";
                  }
                }}
                disabled={!selectedFile && !result}
              >
                Reset
              </button>
            </div>
          </form>

          <article className={`status-card status-${status.kind}`}>
            <p className="status-label">Status</p>
            <p className="status-message">{status.message}</p>
          </article>

          <div className="metric-strip">
            <Metric label="Revealed" value={String(cows.length).padStart(2, "0")} />
            <Metric label="Board" value={result ? `${result.board.grid_size}×${result.board.grid_size}` : "--"} />
          </div>
        </section>

        <section className="viewer-panel reveal reveal-3">
          <div className="panel-header">
            <p className="panel-kicker">Preview</p>
            <h2>Board Preview</h2>
          </div>

          <div className={`board-stage ${previewUrl ? "board-stage-active" : ""}`}>
            {previewUrl ? (
              <div className="image-frame">
                <img className="board-image" src={previewUrl} alt="Uploaded XiaoxiaoNiu screenshot" />
                {result ? (
                  <div className="overlay-layer" aria-hidden="true">
                    <div
                      className="board-outline"
                      style={rectStyleFromNormalized(result.board.bounding_box_normalized)}
                    />
                    {result.board.cows.map((cow) => (
                      <div
                        key={`${cow.row_index}-${cow.col_index}`}
                        className="cow-pin"
                        style={{
                          left: `${cow.center_normalized.x * 100}%`,
                          top: `${cow.center_normalized.y * 100}%`,
                          animationDelay: `${getCowDropDelay(cow)}ms`,
                        }}
                      >
                        <span className="cow-pin-icon" aria-hidden="true">🐮</span>
                        <span className="cow-pin-tag">{cow.row},{cow.col}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="empty-stage">
                <span className="empty-stage-icon" aria-hidden="true">🖼️</span>
                <p>Upload a screenshot to preview the board.</p>
                <span>The board image and cow positions will appear here.</span>
              </div>
            )}
          </div>
        </section>

        <section className="results-panel reveal reveal-4">
          <div className="panel-header">
            <p className="panel-kicker">Results</p>
            <h2>Results</h2>
          </div>

          <div className="cow-list">
            {cows.length ? (
              cows.map((cow, index) => (
                <article className="cow-row" key={`${cow.row_index}-${cow.col_index}`}>
                  <span className="cow-index">{String(index + 1).padStart(2, "0")}</span>
                  <div className="cow-meta">
                    <p>Row {cow.row}, Col {cow.col}</p>
                    <p className="cow-coords">
                      x {cow.center_px.x.toFixed(2)} / y {cow.center_px.y.toFixed(2)}
                    </p>
                  </div>
                  <span className="cow-chip">Pinned</span>
                </article>
              ))
            ) : (
              <div className="empty-list">
                <p>No results yet.</p>
                <span>Upload and solve a board to see cow positions here.</span>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function VisitCounter({ count, isAnimated }) {
  return (
    <div className={`visit-counter${isAnimated ? " visit-counter-animated" : ""}`}>
      <span className="visit-counter-label">Visits</span>
      <strong>{formatVisitCount(count)}</strong>
    </div>
  );
}

function getCowDropDelay(cow) {
  return cow.row_index * COW_DROP_STAGGER_MS + (cow.col_index % 3) * COW_DROP_VARIATION_MS;
}

function formatVisitCount(count) {
  if (typeof count !== "number") {
    return "—";
  }
  return count.toLocaleString("en-US");
}

function rectStyleFromNormalized(rect) {
  return {
    left: `${rect.x * 100}%`,
    top: `${rect.y * 100}%`,
    width: `${rect.width * 100}%`,
    height: `${rect.height * 100}%`,
  };
}

export default App;
