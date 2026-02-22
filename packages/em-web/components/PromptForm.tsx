"use client";

import { useState } from "react";

interface PromptField {
  name: string;
  label: string;
  type: string;
  options?: string[];
  default?: any;
}

interface Props {
  fields: PromptField[];
  onSubmit: (answers: Record<string, any>) => void;
}

export default function PromptForm({ fields, onSubmit }: Props) {
  const [values, setValues] = useState<Record<string, any>>(() => {
    const init: Record<string, any> = {};
    for (const f of fields) {
      if (f.default !== undefined) init[f.name] = f.default;
      else if (f.type === "confirm") init[f.name] = false;
      else if (f.type === "number") init[f.name] = 0;
      else init[f.name] = "";
    }
    return init;
  });

  const handleChange = (name: string, value: any) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <div style={{ background: "#1a1a2e", border: "1px solid #4444aa", borderRadius: 8, padding: "1.5rem", marginTop: "1rem" }}>
      <h3 style={{ marginTop: 0, fontSize: "1rem" }}>User Input Required</h3>
      {fields.map((field) => (
        <div key={field.name} style={{ marginBottom: "0.8rem" }}>
          <label style={{ display: "block", fontSize: "0.85rem", marginBottom: "0.3rem", color: "#aaa" }}>
            {field.label}
          </label>
          {field.type === "confirm" ? (
            <label style={{ fontSize: "0.85rem" }}>
              <input
                type="checkbox"
                checked={!!values[field.name]}
                onChange={(e) => handleChange(field.name, e.target.checked)}
              />{" "}
              Yes
            </label>
          ) : field.type === "select" && field.options ? (
            <select
              value={values[field.name] || ""}
              onChange={(e) => handleChange(field.name, e.target.value)}
              style={{ background: "#222", color: "#eee", border: "1px solid #555", borderRadius: 4, padding: "0.3rem" }}
            >
              {field.options.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          ) : field.type === "number" ? (
            <input
              type="number"
              value={values[field.name] || 0}
              onChange={(e) => handleChange(field.name, Number(e.target.value))}
              style={{ background: "#222", color: "#eee", border: "1px solid #555", borderRadius: 4, padding: "0.3rem 0.5rem" }}
            />
          ) : (
            <input
              type="text"
              value={values[field.name] || ""}
              onChange={(e) => handleChange(field.name, e.target.value)}
              style={{
                width: "100%", background: "#222", color: "#eee",
                border: "1px solid #555", borderRadius: 4, padding: "0.3rem 0.5rem",
              }}
            />
          )}
        </div>
      ))}
      <button
        onClick={() => onSubmit(values)}
        style={{
          padding: "0.5rem 1.2rem", background: "#7c3aed", color: "white",
          border: "none", borderRadius: 6, cursor: "pointer", fontSize: "0.85rem",
        }}
      >
        Submit Answers
      </button>
    </div>
  );
}
