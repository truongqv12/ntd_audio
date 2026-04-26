import { memo, useCallback, useState, type ChangeEvent } from "react";
import { bulkImportRows } from "../api";
import { useI18n, type Locale } from "../i18n";
import type { BulkImportResponse } from "../types";

const COPY: Record<Locale, Record<string, string>> = {
  en: {
    title: "Import script lines",
    description: "Drop a .txt or .csv to bulk-create script rows for this project.",
    file: "File",
    format: "Format",
    txt: ".txt (one row per line)",
    csv: ".csv (header + columns)",
    txtSplit: "Split mode",
    txtSplitLine: "One line per row",
    txtSplitBlank: "Blank line separates paragraphs",
    textColumn: "Text column name",
    voiceColumn: "Voice column (optional)",
    speakerColumn: "Speaker column (optional)",
    titleColumn: "Title column (optional)",
    defaultProvider: "Default provider key (optional)",
    defaultVoice: "Default voice id (optional)",
    autoEnqueue: "Queue jobs immediately after import",
    cancel: "Cancel",
    submit: "Import",
    submitting: "Importing…",
    error: "Import failed",
  },
  vi: {
    title: "Nhập danh sách câu",
    description: "Thả file .txt hoặc .csv để tạo nhanh nhiều dòng cho project này.",
    file: "Tệp",
    format: "Định dạng",
    txt: ".txt (mỗi dòng 1 row)",
    csv: ".csv (có header + cột)",
    txtSplit: "Chế độ tách",
    txtSplitLine: "Mỗi dòng = 1 row",
    txtSplitBlank: "Tách theo dòng trống (đoạn văn)",
    textColumn: "Tên cột text",
    voiceColumn: "Cột voice (tùy chọn)",
    speakerColumn: "Cột speaker (tùy chọn)",
    titleColumn: "Cột title (tùy chọn)",
    defaultProvider: "Provider key mặc định (tùy chọn)",
    defaultVoice: "Voice id mặc định (tùy chọn)",
    autoEnqueue: "Tự động chạy sau khi import",
    cancel: "Hủy",
    submit: "Nhập",
    submitting: "Đang nhập…",
    error: "Nhập thất bại",
  },
};

type Props = {
  open: boolean;
  projectKey: string;
  onClose: () => void;
  onImported: (response: BulkImportResponse) => void;
};

export const BulkImportDialog = memo(function BulkImportDialog({
  open,
  projectKey,
  onClose,
  onImported,
}: Props) {
  const { locale } = useI18n();
  const t = COPY[locale];

  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState<"txt" | "csv">("txt");
  const [txtSplit, setTxtSplit] = useState<"line" | "blank-line">("line");
  const [textColumn, setTextColumn] = useState("text");
  const [voiceColumn, setVoiceColumn] = useState("voice");
  const [speakerColumn, setSpeakerColumn] = useState("speaker");
  const [titleColumn, setTitleColumn] = useState("");
  const [defaultProvider, setDefaultProvider] = useState("");
  const [defaultVoice, setDefaultVoice] = useState("");
  const [autoEnqueue, setAutoEnqueue] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFileChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0] ?? null;
    setFile(next);
    if (next) {
      const lower = next.name.toLowerCase();
      if (lower.endsWith(".csv")) setFormat("csv");
      else if (lower.endsWith(".txt")) setFormat("txt");
    }
  }, []);

  const onSubmit = useCallback(async () => {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await bulkImportRows(projectKey, {
        file,
        format,
        txt_split: txtSplit,
        text_column: textColumn || undefined,
        voice_column: voiceColumn || undefined,
        speaker_column: speakerColumn || undefined,
        title_column: titleColumn || undefined,
        default_provider_key: defaultProvider || undefined,
        default_voice_id: defaultVoice || undefined,
        auto_enqueue: autoEnqueue,
      });
      onImported(response);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.error);
    } finally {
      setSubmitting(false);
    }
  }, [
    autoEnqueue,
    defaultProvider,
    defaultVoice,
    file,
    format,
    onClose,
    onImported,
    projectKey,
    speakerColumn,
    t.error,
    textColumn,
    titleColumn,
    txtSplit,
    voiceColumn,
  ]);

  if (!open) return null;

  return (
    <div className="voice-dialog-overlay" role="dialog" aria-modal="true" aria-label={t.title}>
      <div className="voice-dialog-shell panel-surface" style={{ maxWidth: 640 }}>
        <div className="voice-dialog-header">
          <div>
            <p className="eyebrow">{t.title}</p>
            <h3 style={{ margin: 0 }}>{t.title}</h3>
            <p className="muted-copy" style={{ marginTop: 4 }}>
              {t.description}
            </p>
          </div>
          <button type="button" className="ghost-btn" onClick={onClose} disabled={submitting}>
            ×
          </button>
        </div>

        <div style={{ display: "grid", gap: 14, padding: "16px 0" }}>
          <label>
            <div className="field-label">{t.file}</div>
            <input type="file" accept=".txt,.csv,text/plain,text/csv" onChange={onFileChange} />
          </label>

          <label>
            <div className="field-label">{t.format}</div>
            <select value={format} onChange={(e) => setFormat(e.target.value as "txt" | "csv")}>
              <option value="txt">{t.txt}</option>
              <option value="csv">{t.csv}</option>
            </select>
          </label>

          {format === "txt" ? (
            <label>
              <div className="field-label">{t.txtSplit}</div>
              <select value={txtSplit} onChange={(e) => setTxtSplit(e.target.value as "line" | "blank-line")}>
                <option value="line">{t.txtSplitLine}</option>
                <option value="blank-line">{t.txtSplitBlank}</option>
              </select>
            </label>
          ) : (
            <div style={{ display: "grid", gap: 10, gridTemplateColumns: "1fr 1fr" }}>
              <label>
                <div className="field-label">{t.textColumn}</div>
                <input value={textColumn} onChange={(e) => setTextColumn(e.target.value)} />
              </label>
              <label>
                <div className="field-label">{t.voiceColumn}</div>
                <input value={voiceColumn} onChange={(e) => setVoiceColumn(e.target.value)} />
              </label>
              <label>
                <div className="field-label">{t.speakerColumn}</div>
                <input value={speakerColumn} onChange={(e) => setSpeakerColumn(e.target.value)} />
              </label>
              <label>
                <div className="field-label">{t.titleColumn}</div>
                <input value={titleColumn} onChange={(e) => setTitleColumn(e.target.value)} />
              </label>
            </div>
          )}

          <div style={{ display: "grid", gap: 10, gridTemplateColumns: "1fr 1fr" }}>
            <label>
              <div className="field-label">{t.defaultProvider}</div>
              <input
                value={defaultProvider}
                onChange={(e) => setDefaultProvider(e.target.value)}
                placeholder="voicevox"
              />
            </label>
            <label>
              <div className="field-label">{t.defaultVoice}</div>
              <input value={defaultVoice} onChange={(e) => setDefaultVoice(e.target.value)} placeholder="0" />
            </label>
          </div>

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={autoEnqueue} onChange={(e) => setAutoEnqueue(e.target.checked)} />
            <span>{t.autoEnqueue}</span>
          </label>

          {error ? <p className="error-text">{error}</p> : null}
        </div>

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button type="button" className="ghost-btn" onClick={onClose} disabled={submitting}>
            {t.cancel}
          </button>
          <button type="button" className="primary-btn" onClick={onSubmit} disabled={!file || submitting}>
            {submitting ? t.submitting : t.submit}
          </button>
        </div>
      </div>
    </div>
  );
});
