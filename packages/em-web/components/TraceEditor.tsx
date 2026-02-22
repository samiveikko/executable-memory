"use client";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onLoadExample: () => void;
}

export default function TraceEditor({ value, onChange, onLoadExample }: Props) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
        <h2 style={{ fontSize: "1.1rem", margin: 0 }}>Agent Trace (JSON)</h2>
        <button
          onClick={onLoadExample}
          style={{
            padding: "0.3rem 0.8rem", background: "#333", color: "#ccc",
            border: "1px solid #555", borderRadius: 4, cursor: "pointer", fontSize: "0.8rem",
          }}
        >
          Load Example
        </button>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        style={{
          width: "100%", height: 400, background: "#111", color: "#e0e0e0",
          border: "1px solid #333", borderRadius: 8, padding: "1rem",
          fontFamily: "monospace", fontSize: "0.85rem", resize: "vertical",
        }}
      />
    </div>
  );
}
