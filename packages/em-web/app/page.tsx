"use client";

import { useState } from "react";
import TraceEditor from "@/components/TraceEditor";
import RoutineView from "@/components/RoutineView";
import RunPanel from "@/components/RunPanel";
import PromptForm from "@/components/PromptForm";

const EXAMPLE_TRACE = `{
  "version": "1",
  "app": {"name": "csv-agent", "version": "1.0"},
  "mission": {
    "goal": "Fetch and summarize a CSV file",
    "input_summary": {"url": "fixture://demo.csv"}
  },
  "events": [
    {"type": "tool_call", "seq": 0, "tool": "fetch_csv", "args": {"url": "fixture://demo.csv"}, "result": "name,dept,hours\\nAlice,Eng,40\\nBob,Mkt,35"},
    {"type": "udf_call", "seq": 1, "function": "parse_csv", "args": {"raw": "name,dept,hours\\nAlice,Eng,40\\nBob,Mkt,35"}, "result": [{"name":"Alice","dept":"Eng","hours":40}]},
    {"type": "approval", "seq": 2, "prompt": "Proceed?", "answer": true}
  ],
  "final_output": {"rows": 2}
}`;

type CompileResult = { routine_yaml: string; udf_source: string } | null;
type RunResultType = { run_id: string; status: string; output: any; pending_prompt?: string; prompt_fields?: any[] } | null;

export default function Home() {
  const [trace, setTrace] = useState(EXAMPLE_TRACE);
  const [compiled, setCompiled] = useState<CompileResult>(null);
  const [runResult, setRunResult] = useState<RunResultType>(null);
  const [input, setInput] = useState('{"url": "fixture://demo.csv"}');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompile = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trace: JSON.parse(trace) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Compile failed");
      setCompiled(data);
      setRunResult(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (!compiled) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ routine_yaml: compiled.routine_yaml, udf_source: compiled.udf_source, input: JSON.parse(input) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Run failed");
      setRunResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async (answers: Record<string, any>) => {
    if (!runResult) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runResult.run_id, answers }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Resume failed");
      setRunResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: 1200, margin: "0 auto", padding: "2rem" }}>
      <h1 style={{ fontSize: "1.8rem", marginBottom: "0.5rem" }}>Executable Memory</h1>
      <p style={{ color: "#888", marginBottom: "2rem" }}>
        Convert agent traces into deterministic routines — no LLM required.
      </p>

      {error && (
        <div style={{ background: "#3a1111", border: "1px solid #ff4444", borderRadius: 8, padding: "1rem", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
        <div>
          <TraceEditor value={trace} onChange={setTrace} onLoadExample={() => setTrace(EXAMPLE_TRACE)} />
          <button
            onClick={handleCompile}
            disabled={loading}
            style={{
              marginTop: "0.5rem", padding: "0.6rem 1.5rem", background: "#2563eb",
              color: "white", border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.9rem",
            }}
          >
            {loading ? "Compiling..." : "Compile Trace"}
          </button>
        </div>

        <div>
          {compiled && <RoutineView yaml={compiled.routine_yaml} udf={compiled.udf_source} />}
        </div>
      </div>

      {compiled && (
        <div style={{ marginTop: "2rem" }}>
          <RunPanel input={input} onInputChange={setInput} onRun={handleRun} loading={loading} result={runResult} />
        </div>
      )}

      {runResult?.status === "needs_input" && runResult.prompt_fields && (
        <PromptForm fields={runResult.prompt_fields} onSubmit={handleResume} />
      )}
    </main>
  );
}
