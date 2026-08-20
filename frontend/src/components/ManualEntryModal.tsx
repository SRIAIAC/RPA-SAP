import { useState } from "react";
import { triggerRun } from "../api";
import { MANUAL_ENTRY_FIELDS } from "../manualEntryFields";
import type { Run } from "../types";

interface Props {
  workflow: { id: number; key: string; name: string };
  onClose: () => void;
  onSubmitted: (run: Run) => void;
}

export default function ManualEntryModal({ workflow, onClose, onSubmitted }: Props) {
  const fields = MANUAL_ENTRY_FIELDS[workflow.key] ?? [];
  const [values, setValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const manualInput: Record<string, string> = {};
      for (const field of fields) {
        const v = values[field.name];
        if (v !== undefined && v.trim() !== "") manualInput[field.name] = v.trim();
      }
      const run = await triggerRun(workflow.id, manualInput);
      onSubmitted(run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to trigger run");
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="dept-heading">Enter manually — {workflow.name}</h3>
        <p className="modal-subtitle">
          {fields.length > 0
            ? "Leave a field blank to use the workflow's default demo data. Any code or number you type is looked up for real — if it doesn't exist in SAP/non-SAP, the run correctly raises a “not found” exception."
            : "This workflow has no manual fields to enter — it will run against its default demo data."}
        </p>
        {error && <div className="form-error">{error}</div>}
        <form onSubmit={handleSubmit} className="stack-md">
          {fields.map((field) => (
            <label key={field.name}>
              {field.label}
              {field.type === "textarea" ? (
                <textarea
                  rows={3}
                  value={values[field.name] ?? ""}
                  placeholder={field.placeholder}
                  onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
                />
              ) : (
                <input
                  type={field.type === "number" ? "number" : "text"}
                  value={values[field.name] ?? ""}
                  placeholder={field.placeholder}
                  onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
                />
              )}
            </label>
          ))}
          <div className="modal-actions">
            <button type="button" className="btn-ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Starting…" : "Run with these values"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
