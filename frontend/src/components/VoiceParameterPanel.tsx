import { memo, useMemo } from "react";
import type { ProviderParamField } from "../types";

export const VoiceParameterPanel = memo(function VoiceParameterPanel({
  providerKey,
  schemas,
  values,
  onChange,
  compact = false,
}: {
  providerKey?: string | null;
  schemas: Record<string, ProviderParamField[]>;
  values: Record<string, unknown>;
  onChange: (key: string, value: string | number | boolean) => void;
  compact?: boolean;
}) {
  const fields = useMemo(() => (providerKey ? schemas[providerKey] ?? [] : []), [providerKey, schemas]);

  if (!providerKey) {
    return <p className="muted-copy compact-copy">Choose a voice to see engine-specific settings.</p>;
  }

  if (fields.length === 0) {
    return <p className="muted-copy compact-copy">No adjustable parameters surfaced for this provider yet.</p>;
  }

  return (
    <div className={compact ? "voice-param-grid voice-param-grid-compact" : "voice-param-grid"}>
      {fields.map((field) => {
        const value = values[field.key] ?? field.default ?? (field.kind === "boolean" ? false : "");
        return (
          <label className="voice-param-field" key={field.key}>
            <span className="voice-param-label">
              {field.label}
              {field.unit ? <small>{field.unit}</small> : null}
            </span>
            {field.kind === "textarea" ? (
              <textarea
                rows={compact ? 2 : 3}
                value={String(value ?? "")}
                onChange={(event) => onChange(field.key, event.target.value)}
              />
            ) : field.kind === "text" ? (
              <input value={String(value ?? "")} onChange={(event) => onChange(field.key, event.target.value)} />
            ) : field.kind === "boolean" ? (
              <label className="switch-row">
                <input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(field.key, event.target.checked)} />
                <span>{Boolean(value) ? "On" : "Off"}</span>
              </label>
            ) : field.kind === "select" ? (
              <select value={String(value ?? "")} onChange={(event) => onChange(field.key, event.target.value)}>
                {field.options.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            ) : (
              <div className="slider-row">
                <input
                  type="range"
                  min={field.min ?? 0}
                  max={field.max ?? 2}
                  step={field.step ?? 0.01}
                  value={Number(value ?? field.default ?? 0)}
                  onChange={(event) => onChange(field.key, Number(event.target.value))}
                />
                <strong>{Number(value ?? field.default ?? 0).toFixed((field.step ?? 1) < 1 ? 2 : 0)}</strong>
              </div>
            )}
            {field.description ? <small className="muted-copy compact-copy">{field.description}</small> : null}
          </label>
        );
      })}
    </div>
  );
});
