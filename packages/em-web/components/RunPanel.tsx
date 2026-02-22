"use client";

interface Props {
  input: string;
  onInputChange: (v: string) => void;
  onRun: () => void;
  loading: boolean;
  result: { run_id: string; status: string; output: any; failure?: any } | null;
}

export default function RunPanel({ input, onInputChange, onRun, loading, result }: Props) {
  const statusColor = result?.status === "ok" ? "#22c55e" : result?.status === "failed" ? "#ef4444" : "#eab308";

  return (
    <div style={{ background: "#111", border: "1px solid #333", borderRadius: 8, padding: "1.5rem" }}>
      <h2 style={{ fontSize: "1.1rem", marginTop: 0 }}>Run Routine</h2>

      <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: "0.85rem", color: "#999" }}>Input JSON</label>
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            spellCheck={false}
            style={{
              width: "100%", height: 80, background: "#0a0a0a", color: "#e0e0e0",
              border: "1px solid #333", borderRadius: 6, padding: "0.5rem",
              fontFamily: "monospace", fontSize: "0.8rem",
            }}
          />
          <button
            onClick={onRun}
            disabled={loading}
            style={{
              marginTop: "0.5rem", padding: "0.5rem 1.2rem", background: "#16a34a",
              color: "white", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem",
            }}
          >
            {loading ? "Running..." : "Run"}
          </button>
        </div>

        {result && (
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: "0.85rem", marginBottom: "0.5rem" }}>
              Status: <span style={{ color: statusColor, fontWeight: "bold" }}>{result.status}</span>
            </div>
            {result.status === "ok" && (
              <pre style={{ background: "#0a0a0a", padding: "0.5rem", borderRadius: 6, fontSize: "0.8rem", overflow: "auto", maxHeight: 200 }}>
                {JSON.stringify(result.output, null, 2)}
              </pre>
            )}
            {result.status === "failed" && result.failure && (
              <pre style={{ background: "#1a0505", padding: "0.5rem", borderRadius: 6, fontSize: "0.8rem", color: "#ff8888" }}>
                {result.failure.message}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
