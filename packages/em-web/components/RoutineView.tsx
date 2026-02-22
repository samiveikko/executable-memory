"use client";

import { useState } from "react";

interface Props {
  yaml: string;
  udf: string;
}

export default function RoutineView({ yaml, udf }: Props) {
  const [tab, setTab] = useState<"yaml" | "udf">("yaml");

  const tabStyle = (active: boolean) => ({
    padding: "0.4rem 1rem",
    background: active ? "#2563eb" : "#222",
    color: active ? "white" : "#999",
    border: "none",
    borderRadius: "4px 4px 0 0",
    cursor: "pointer" as const,
    fontSize: "0.85rem",
  });

  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", marginBottom: "0.5rem" }}>Compiled Routine</h2>
      <div>
        <button onClick={() => setTab("yaml")} style={tabStyle(tab === "yaml")}>routine.yaml</button>
        <button onClick={() => setTab("udf")} style={tabStyle(tab === "udf")}>udf.py</button>
      </div>
      <pre
        style={{
          background: "#111", border: "1px solid #333", borderRadius: "0 8px 8px 8px",
          padding: "1rem", overflow: "auto", maxHeight: 400,
          fontSize: "0.8rem", margin: 0,
        }}
      >
        {tab === "yaml" ? yaml : udf}
      </pre>
    </div>
  );
}
