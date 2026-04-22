import { startTransition, useEffect, useRef, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const initialStatus = {
  kind: "idle",
  message: "Upload a board screenshot and reveal every hidden cow.",
};

function App() {
  const [visitCount, setVisitCount] = useState(null);
  const [status, setStatus] = useState(initialStatus);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    async function registerVisit() {
      try {
        const sessionKey = "xiaoxiaoniu-visit-registered";
        const hasTrackedInSession = window.sessionStorage.getItem(sessionKey) === "1";
        if (!hasTrackedInSession) {
          window.sessionStorage.setItem(sessionKey, "1");
        }
        const response = await fetch(`${API_BASE_URL}/api/site-visits`, {
          method: hasTrackedInSession ? "GET" : "POST",
        });
        if (!response.ok) {
          throw new Error("Visit counter request failed.");
        }
        const payload = await response.json();
        if (isMounted) {
          setVisitCount(payload?.data?.total_visits ?? null);
        }
      } catch {
        window.sessionStorage.removeItem("xiaoxiaoniu-visit-registered");
        if (isMounted) {
          setVisitCount(null);
        }
      }
    }

    registerVisit();

    return () => {
      isMounted = false;
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
        message: `${file.name} is ready. Scan the board when you want.`,
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
        message: "Reading the board and pinning the herd...",
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
          message: `Found ${payload.data.board.cows.length} cows on this board.`,
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
      <div className="ambient ambient-left" aria-hidden="true" />
      <div className="ambient ambient-right" aria-hidden="true" />
      <header className="hero-panel">
        <div className="hero-copy reveal reveal-1">
          <div className="brand-row">
            <div className="brand-mark" aria-hidden="true">
              🐮
            </div>
            <div className="brand-copy">
              <p className="eyebrow">XiaoxiaoNiu</p>
              <strong>Tactical Board</strong>
            </div>
            <div className="hero-status-wrap">
              <VisitCounter count={visitCount} />
            </div>
          </div>
          <h1>Find every hidden cow in one pass.</h1>
          <p className="hero-text">
            Turn a puzzle screenshot into a clean, confident answer. Upload the board and see every
            cow appear exactly where it belongs.
          </p>
        </div>
      </header>

      <main className="workspace">
        <section className="control-panel reveal reveal-2">
          <div className="panel-header">
            <p className="panel-kicker">Mission Input</p>
            <h2>Field Upload</h2>
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
              <span className="dropzone-icon">✦</span>
              <span className="dropzone-label">
                {selectedFile ? selectedFile.name : "Choose screenshot"}
              </span>
              <span className="dropzone-hint">JPEG, PNG or any image the backend can decode</span>
            </button>

            <div className="action-row">
              <button className="primary-button" type="submit" disabled={!selectedFile || isSubmitting}>
                {isSubmitting ? "Scanning..." : "Find All Cows"}
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
            <Metric label="Visits" value={formatVisitCount(visitCount)} />
            <Metric label="Pinned" value={String(cows.length).padStart(2, "0")} />
            <Metric label="Grid" value={result ? `${result.board.grid_size}×${result.board.grid_size}` : "--"} />
          </div>
        </section>

        <section className="viewer-panel reveal reveal-3">
          <div className="panel-header">
            <p className="panel-kicker">Overlay View</p>
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
                    {result.board.cows.map((cow, index) => (
                      <div
                        key={`${cow.row_index}-${cow.col_index}`}
                        className="cow-pin"
                        style={{
                          left: `${cow.center_normalized.x * 100}%`,
                          top: `${cow.center_normalized.y * 100}%`,
                          animationDelay: `${index * 80}ms`,
                        }}
                      >
                        <span className="cow-pin-core" />
                        <span className="cow-pin-tag">{cow.row},{cow.col}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="empty-stage">
                <span className="empty-stage-mark">牧</span>
                <p>Upload a screenshot to preview the tactical overlay.</p>
              </div>
            )}
          </div>
        </section>

        <section className="results-panel reveal reveal-4">
          <div className="panel-header">
            <p className="panel-kicker">Resolved Positions</p>
            <h2>Herd Ledger</h2>
          </div>

          <div className="cow-list">
            {cows.length ? (
              cows.map((cow, index) => (
                <article className="cow-row" key={`${cow.row_index}-${cow.col_index}`}>
                  <span className="cow-index">{String(index + 1).padStart(2, "0")}</span>
                  <div className="cow-meta">
                    <p>
                      Row {cow.row}, Col {cow.col}
                    </p>
                    <p className="cow-coords">
                      x {cow.center_px.x.toFixed(2)} / y {cow.center_px.y.toFixed(2)}
                    </p>
                  </div>
                  <span className="cow-chip">Pinned</span>
                </article>
              ))
            ) : (
              <div className="empty-list">
                <p>No cows pinned yet.</p>
                <span>The backend result will populate this ledger automatically.</span>
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

function VisitCounter({ count }) {
  return (
    <div className="visit-counter">
      <span className="visit-counter-label">Visits</span>
      <strong>{formatVisitCount(count)}</strong>
    </div>
  );
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
