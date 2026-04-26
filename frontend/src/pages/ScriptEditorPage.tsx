import { memo, useCallback, useEffect, useMemo, useState } from "react";
import {
  artifactUrl,
  downloadProjectArtifactsZip,
  downloadProjectExport,
  downloadProjectSubtitles,
  fetchProjectRows,
  mergeProjectRows,
  previewRowSynthesis,
  queueProjectRows,
  replaceProjectRows,
} from "../api";
import { BulkImportDialog } from "../components/BulkImportDialog";
import { Panel } from "../components/Panel";
import { StatusBadge } from "../components/StatusBadge";
import { VoiceAvatar } from "../components/VoiceAvatar";
import { VoicePickerDialog } from "../components/VoicePickerDialog";
import { VoiceParameterPanel } from "../components/VoiceParameterPanel";
import { useI18n, type Locale } from "../i18n";
import { formatJobDuration } from "../lib/format";
import type {
  Project,
  ProjectMergeResponse,
  ProjectScriptRow,
  ProviderParamField,
  ProviderSummary,
  VoiceCatalogEntry,
} from "../types";

type DraftRow = {
  local_id: string;
  id?: string;
  row_index: number;
  title: string;
  source_text: string;
  speaker_label: string;
  provider_key: string;
  provider_voice_id: string;
  output_format: string;
  params: Record<string, unknown>;
  is_enabled: boolean;
  join_to_master: boolean;
  status: string;
  last_job_id?: string | null;
  last_artifact_download_url?: string | null;
  duration_seconds?: number | null;
  error_message?: string | null;
};

type PickerTarget = { mode: "row"; localId: string } | { mode: "bulk" } | null;

const COPY: Record<Locale, Record<string, string>> = {
  en: {
    title: "Script line editor",
    description:
      "Edit long scripts row-by-row, assign voices per line, generate only changed lines and merge completed audio into a master file.",
    project: "Project",
    importTitle: "Import script",
    importDescription: "Paste text and split by non-empty lines. Save after editing before queueing.",
    importPlaceholder: "Paste one sentence or paragraph per line...",
    splitLines: "Split into rows",
    addRow: "Add row",
    saveRows: "Save rows",
    saving: "Saving...",
    saved: "Rows saved",
    dirty: "Unsaved changes",
    rows: "Rows",
    activeRows: "Enabled rows",
    completedRows: "Completed rows",
    selectedRows: "Selected rows",
    line: "Line",
    titleField: "Title",
    speakerField: "Speaker",
    speakerPlaceholder: "Speaker label (optional)",
    text: "Text",
    voice: "Voice",
    format: "Format",
    enabled: "Enabled",
    join: "Join",
    status: "Status",
    output: "Output",
    chooseVoice: "Choose voice",
    bulkVoice: "Set voice for selected rows",
    applyVoiceHint: "If no rows are selected, the bulk voice action applies to all enabled rows.",
    noVoice: "No voice selected",
    inherit: "Inherit",
    play: "Play",
    download: "Download",
    deleteSelected: "Delete selected",
    duplicateSelected: "Duplicate selected",
    queueSelected: "Queue selected",
    queueEnabled: "Queue enabled rows",
    queueAndMerge: "Queue enabled + merge",
    bulkImport: "Import .txt / .csv",
    downloadZip: "Download all .zip",
    downloadZipEmpty: "No completed rows to download",
    preview: "Preview",
    previewing: "Generating…",
    previewError: "Preview failed",
    mergeCompleted: "Merge completed",
    mergeFormat: "Merge format",
    silence: "Silence ms",
    masterReady: "Master artifact ready",
    noRows: "No script rows yet. Import text or add a row to begin.",
    missingVoice: "Missing voice",
    previewUnavailable: "No artifact yet",
    loadError: "Unable to load project rows",
    saveError: "Unable to save project rows",
    queueError: "Unable to queue rows",
    mergeError: "Unable to merge rows",
    exportProject: "Export project (.zip)",
    exportError: "Unable to export project",
    downloadSubtitles: "Download subtitles",
    subtitlesError: "Unable to download subtitles",
    reorderUp: "Move up",
    reorderDown: "Move down",
  },
  vi: {
    title: "Editor từng dòng script",
    description:
      "Sửa script dài theo từng dòng, gán voice riêng cho từng dòng, chỉ render lại dòng cần thiết và nối audio đã xong thành file master.",
    project: "Project",
    importTitle: "Import script",
    importDescription: "Dán text và tách theo các dòng không rỗng. Sau khi sửa nên lưu trước khi queue.",
    importPlaceholder: "Dán mỗi câu hoặc mỗi đoạn trên một dòng...",
    splitLines: "Tách thành dòng",
    addRow: "Thêm dòng",
    saveRows: "Lưu dòng",
    saving: "Đang lưu...",
    saved: "Đã lưu dòng",
    dirty: "Có thay đổi chưa lưu",
    rows: "Dòng",
    activeRows: "Dòng bật",
    completedRows: "Dòng đã xong",
    selectedRows: "Dòng đang chọn",
    line: "Dòng",
    titleField: "Tiêu đề",
    speakerField: "Speaker",
    speakerPlaceholder: "Tên speaker (tuỳ chọn)",
    text: "Text",
    voice: "Voice",
    format: "Định dạng",
    enabled: "Bật",
    join: "Nối",
    status: "Trạng thái",
    output: "Output",
    chooseVoice: "Chọn voice",
    bulkVoice: "Gán voice cho dòng đã chọn",
    applyVoiceHint: "Nếu chưa chọn dòng nào, thao tác gán voice sẽ áp dụng cho tất cả dòng đang bật.",
    noVoice: "Chưa chọn voice",
    inherit: "Kế thừa",
    play: "Nghe",
    download: "Tải về",
    deleteSelected: "Xoá dòng đã chọn",
    duplicateSelected: "Nhân bản dòng đã chọn",
    queueSelected: "Render dòng đã chọn",
    queueEnabled: "Render các dòng bật",
    queueAndMerge: "Render dòng bật + nối",
    bulkImport: "Nhập .txt / .csv",
    downloadZip: "Tải tất cả .zip",
    downloadZipEmpty: "Chưa có dòng nào hoàn tất để tải",
    preview: "Nghe thử",
    previewing: "Đang tạo…",
    previewError: "Nghe thử lỗi",
    mergeCompleted: "Nối các dòng đã xong",
    mergeFormat: "Định dạng master",
    silence: "Khoảng lặng ms",
    masterReady: "File master đã sẵn sàng",
    noRows: "Chưa có dòng script. Import text hoặc thêm dòng để bắt đầu.",
    missingVoice: "Thiếu voice",
    previewUnavailable: "Chưa có artifact",
    loadError: "Không tải được dòng project",
    saveError: "Không lưu được dòng project",
    queueError: "Không queue được dòng",
    mergeError: "Không nối được audio",
    exportProject: "Export project (.zip)",
    exportError: "Không export được project",
    downloadSubtitles: "Tải subtitle",
    subtitlesError: "Không tải được subtitle",
    reorderUp: "Đưa lên",
    reorderDown: "Đưa xuống",
  },
};

function rowFromApi(row: ProjectScriptRow): DraftRow {
  return {
    local_id: row.id,
    id: row.id,
    row_index: row.row_index,
    title: row.title ?? "",
    source_text: row.source_text,
    speaker_label: row.speaker_label ?? "",
    provider_key: row.provider_key ?? "",
    provider_voice_id: row.provider_voice_id ?? "",
    output_format: row.output_format ?? "",
    params: row.params ?? {},
    is_enabled: row.is_enabled,
    join_to_master: row.join_to_master,
    status: row.status,
    last_job_id: row.last_job_id,
    last_artifact_download_url: row.last_artifact_download_url,
    duration_seconds: row.duration_seconds,
    error_message: row.error_message,
  };
}

function emptyRow(index: number): DraftRow {
  const now = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return {
    local_id: `draft-${now}`,
    row_index: index,
    title: "",
    source_text: "",
    speaker_label: "",
    provider_key: "",
    provider_voice_id: "",
    output_format: "",
    params: {},
    is_enabled: true,
    join_to_master: true,
    status: "draft",
  };
}

function normalizeRows(rows: DraftRow[]) {
  return rows.map((row, index) => ({ ...row, row_index: index }));
}

function payloadRows(rows: DraftRow[]) {
  return normalizeRows(rows).map((row) => ({
    row_index: row.row_index,
    title: row.title.trim() || undefined,
    source_text: row.source_text,
    speaker_label: row.speaker_label.trim() || undefined,
    provider_key: row.provider_key || undefined,
    provider_voice_id: row.provider_voice_id || undefined,
    output_format: row.output_format || undefined,
    params: row.params ?? {},
    is_enabled: row.is_enabled,
    join_to_master: row.join_to_master,
  }));
}

function buildVoiceKey(providerKey?: string | null, voiceId?: string | null) {
  return providerKey && voiceId ? `${providerKey}:${voiceId}` : "";
}

function defaultParamsForProvider(providerKey: string, schemas: Record<string, ProviderParamField[]>) {
  return Object.fromEntries(
    (schemas[providerKey] ?? []).map((field) => [
      field.key,
      field.default ?? (field.kind === "boolean" ? false : ""),
    ]),
  );
}

export const ScriptEditorPage = memo(function ScriptEditorPage({
  projects,
  providers,
  voices,
  selectedProjectKey,
  onSelectProject,
  eventVersion,
  voiceParameterSchemas,
  mergeDefaults,
}: {
  projects: Project[];
  providers: ProviderSummary[];
  voices: VoiceCatalogEntry[];
  selectedProjectKey: string;
  onSelectProject: (projectKey: string) => void;
  eventVersion: number;
  voiceParameterSchemas: Record<string, ProviderParamField[]>;
  mergeDefaults: Record<string, unknown>;
}) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const [activeProjectKey, setActiveProjectKey] = useState(
    selectedProjectKey || projects[0]?.project_key || "default",
  );
  const [rows, setRows] = useState<DraftRow[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [draggedRowId, setDraggedRowId] = useState<string | null>(null);
  const [importText, setImportText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pickerTarget, setPickerTarget] = useState<PickerTarget>(null);
  const [mergeFormat, setMergeFormat] = useState("wav");
  const [mergeSilenceMs, setMergeSilenceMs] = useState(150);
  const [masterArtifactUrl, setMasterArtifactUrl] = useState<string | null>(null);
  const [bulkImportOpen, setBulkImportOpen] = useState(false);
  const [previewBlobUrls, setPreviewBlobUrls] = useState<Record<string, string>>({});
  const [previewBusyId, setPreviewBusyId] = useState<string | null>(null);
  const [previewErrors, setPreviewErrors] = useState<Record<string, string>>({});

  const project = useMemo(
    () => projects.find((item) => item.project_key === activeProjectKey) ?? null,
    [activeProjectKey, projects],
  );

  useEffect(() => {
    if (!project) return;
    const projectSettings = project.settings ?? {};
    setMergeFormat(String(projectSettings.merge_output_format ?? mergeDefaults.merge_output_format ?? "wav"));
    setMergeSilenceMs(Number(projectSettings.merge_silence_ms ?? mergeDefaults.merge_silence_ms ?? 150));
  }, [project?.project_key, mergeDefaults.merge_output_format, mergeDefaults.merge_silence_ms]);
  const voiceMap = useMemo(
    () => new Map(voices.map((voice) => [buildVoiceKey(voice.provider_key, voice.provider_voice_id), voice])),
    [voices],
  );
  const selectedVoiceForPicker = useMemo(() => {
    if (!pickerTarget || pickerTarget.mode === "bulk") return null;
    const row = rows.find((item) => item.local_id === pickerTarget.localId);
    return row ? (voiceMap.get(buildVoiceKey(row.provider_key, row.provider_voice_id)) ?? null) : null;
  }, [pickerTarget, rows, voiceMap]);

  const stats = useMemo(() => {
    const active = rows.filter((row) => row.is_enabled).length;
    const completed = rows.filter(
      (row) => row.last_artifact_download_url || row.status === "succeeded",
    ).length;
    return { total: rows.length, active, completed, selected: selectedIds.size };
  }, [rows, selectedIds.size]);

  const loadRows = useCallback(
    async (projectKey: string, silent = false) => {
      try {
        if (!silent) setIsLoading(true);
        setError(null);
        const items = await fetchProjectRows(projectKey);
        setRows(items.map(rowFromApi));
        setSelectedIds(new Set());
        setIsDirty(false);
      } catch {
        setError(copy.loadError);
      } finally {
        if (!silent) setIsLoading(false);
      }
    },
    [copy.loadError],
  );

  useEffect(() => {
    if (!activeProjectKey) return;
    void loadRows(activeProjectKey);
  }, [activeProjectKey, loadRows]);

  useEffect(() => {
    if (!activeProjectKey || isDirty) return;
    void loadRows(activeProjectKey, true);
  }, [activeProjectKey, eventVersion, isDirty, loadRows]);

  const updateRows = useCallback((updater: (current: DraftRow[]) => DraftRow[]) => {
    setRows((current) => normalizeRows(updater(current)));
    setIsDirty(true);
    setMessage(null);
  }, []);

  const updateRow = useCallback(
    (localId: string, patch: Partial<DraftRow>) => {
      updateRows((current) => current.map((row) => (row.local_id === localId ? { ...row, ...patch } : row)));
    },
    [updateRows],
  );

  const updateRowParam = useCallback(
    (localId: string, key: string, value: string | number | boolean) => {
      updateRows((current) =>
        current.map((row) =>
          row.local_id === localId ? { ...row, params: { ...(row.params ?? {}), [key]: value } } : row,
        ),
      );
    },
    [updateRows],
  );

  const saveRows = useCallback(async () => {
    try {
      setIsSaving(true);
      setError(null);
      const currentSelectedIndexes = new Set(
        rows.filter((row) => selectedIds.has(row.local_id)).map((row) => row.row_index),
      );
      const saved = await replaceProjectRows(activeProjectKey, payloadRows(rows));
      const nextRows = saved.map(rowFromApi);
      setRows(nextRows);
      setSelectedIds(
        new Set(
          nextRows.filter((row) => currentSelectedIndexes.has(row.row_index)).map((row) => row.local_id),
        ),
      );
      setIsDirty(false);
      setMessage(copy.saved);
      return nextRows;
    } catch {
      setError(copy.saveError);
      return null;
    } finally {
      setIsSaving(false);
    }
  }, [activeProjectKey, copy.saveError, copy.saved, rows, selectedIds]);

  const addRow = useCallback(() => {
    updateRows((current) => [...current, emptyRow(current.length)]);
  }, [updateRows]);

  const importRows = useCallback(() => {
    const imported = importText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((text, index) => ({ ...emptyRow(index), source_text: text, title: `Line ${index + 1}` }));
    if (imported.length > 0) {
      updateRows(() => imported);
      setImportText("");
    }
  }, [importText, updateRows]);

  const deleteSelected = useCallback(() => {
    if (selectedIds.size === 0) return;
    updateRows((current) => current.filter((row) => !selectedIds.has(row.local_id)));
    setSelectedIds(new Set());
  }, [selectedIds, updateRows]);

  const duplicateSelected = useCallback(() => {
    if (selectedIds.size === 0) return;
    updateRows((current) => {
      const copies = current
        .filter((row) => selectedIds.has(row.local_id))
        .map((row, index) => ({
          ...row,
          local_id: `draft-copy-${Date.now()}-${index}`,
          id: undefined,
          status: "draft",
          last_job_id: null,
          last_artifact_download_url: null,
          duration_seconds: null,
          error_message: null,
        }));
      return [...current, ...copies];
    });
  }, [selectedIds, updateRows]);

  const moveRow = useCallback(
    (localId: string, delta: number) => {
      updateRows((current) => {
        const index = current.findIndex((row) => row.local_id === localId);
        const target = index + delta;
        if (index < 0 || target < 0 || target >= current.length) return current;
        const next = [...current];
        const [row] = next.splice(index, 1);
        next.splice(target, 0, row);
        return next;
      });
    },
    [updateRows],
  );

  const moveRowToIndex = useCallback(
    (localId: string, targetIndex: number) => {
      updateRows((current) => {
        const fromIndex = current.findIndex((row) => row.local_id === localId);
        if (fromIndex < 0) return current;
        const clampedTarget = Math.max(0, Math.min(targetIndex, current.length - 1));
        if (clampedTarget === fromIndex) return current;
        const next = [...current];
        const [row] = next.splice(fromIndex, 1);
        next.splice(clampedTarget, 0, row);
        return next;
      });
    },
    [updateRows],
  );

  const toggleSelection = useCallback((localId: string) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(localId)) next.delete(localId);
      else next.add(localId);
      return next;
    });
  }, []);

  const downloadZip = useCallback(async () => {
    try {
      setError(null);
      const blob = await downloadProjectArtifactsZip(activeProjectKey);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${activeProjectKey}-artifacts.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : copy.queueError);
    }
  }, [activeProjectKey, copy.queueError]);

  const completedCount = useMemo(() => rows.filter((row) => row.status === "succeeded").length, [rows]);

  const handlePreviewRow = useCallback(
    async (row: DraftRow) => {
      if (!row.provider_key || !row.provider_voice_id || !row.source_text.trim()) return;
      setPreviewBusyId(row.local_id);
      setPreviewErrors((prev) => {
        if (!(row.local_id in prev)) return prev;
        const next = { ...prev };
        delete next[row.local_id];
        return next;
      });
      try {
        const blob = await previewRowSynthesis(row.provider_key, {
          text: row.source_text,
          voice_id: row.provider_voice_id,
        });
        const url = URL.createObjectURL(blob);
        setPreviewBlobUrls((prev) => {
          const previous = prev[row.local_id];
          if (previous) URL.revokeObjectURL(previous);
          return { ...prev, [row.local_id]: url };
        });
      } catch (err) {
        const detail = err instanceof Error ? err.message : copy.previewError;
        setPreviewErrors((prev) => ({ ...prev, [row.local_id]: detail }));
      } finally {
        setPreviewBusyId(null);
      }
    },
    [copy.previewError],
  );

  useEffect(() => {
    return () => {
      Object.values(previewBlobUrls).forEach((url) => URL.revokeObjectURL(url));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const queueRows = useCallback(
    async (mode: "selected" | "enabled", mergeOutputs = false) => {
      try {
        setError(null);
        const savedRows = isDirty ? await saveRows() : rows;
        if (!savedRows) return;
        let row_ids: string[] | undefined;
        if (mode === "selected") {
          row_ids = savedRows
            .filter((row) => selectedIds.has(row.local_id))
            .map((row) => row.id)
            .filter(Boolean) as string[];
          if (row_ids.length === 0) return;
        }
        await queueProjectRows(activeProjectKey, {
          row_ids,
          merge_outputs: mergeOutputs,
          merge_output_format: mergeFormat,
          merge_silence_ms: mergeSilenceMs,
        });
        await loadRows(activeProjectKey, true);
        setMessage(
          mergeOutputs ? copy.queueAndMerge : mode === "selected" ? copy.queueSelected : copy.queueEnabled,
        );
      } catch {
        setError(copy.queueError);
      }
    },
    [
      activeProjectKey,
      copy.queueAndMerge,
      copy.queueEnabled,
      copy.queueError,
      copy.queueSelected,
      isDirty,
      loadRows,
      mergeFormat,
      mergeSilenceMs,
      rows,
      saveRows,
      selectedIds,
    ],
  );

  const mergeRows = useCallback(async () => {
    try {
      setError(null);
      const result: ProjectMergeResponse = await mergeProjectRows(activeProjectKey, {
        row_ids:
          selectedIds.size > 0
            ? rows.filter((row) => selectedIds.has(row.local_id) && row.id).map((row) => row.id as string)
            : undefined,
        merge_output_format: mergeFormat,
        merge_silence_ms: mergeSilenceMs,
      });
      setMasterArtifactUrl(artifactUrl(result.download_url));
      setMessage(`${copy.masterReady}: ${result.merged_count} ${copy.rows.toLowerCase()}`);
    } catch {
      setError(copy.mergeError);
    }
  }, [
    activeProjectKey,
    copy.masterReady,
    copy.mergeError,
    copy.rows,
    mergeFormat,
    mergeSilenceMs,
    rows,
    selectedIds,
  ]);

  const exportProject = useCallback(async () => {
    try {
      setError(null);
      const blob = await downloadProjectExport(activeProjectKey);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${activeProjectKey}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError(copy.exportError);
    }
  }, [activeProjectKey, copy.exportError]);

  const downloadSubtitles = useCallback(
    async (fileFormat: "srt" | "vtt") => {
      try {
        setError(null);
        const blob = await downloadProjectSubtitles(activeProjectKey, fileFormat, mergeSilenceMs);
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${activeProjectKey}.${fileFormat}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      } catch {
        setError(copy.subtitlesError);
      }
    },
    [activeProjectKey, copy.subtitlesError, mergeSilenceMs],
  );

  const handleVoiceSelected = useCallback(
    (voice: VoiceCatalogEntry) => {
      if (!pickerTarget) return;
      const defaults = defaultParamsForProvider(voice.provider_key, voiceParameterSchemas);
      if (pickerTarget.mode === "row") {
        updateRow(pickerTarget.localId, {
          provider_key: voice.provider_key,
          provider_voice_id: voice.provider_voice_id,
          params: defaults,
        });
      } else {
        updateRows((current) =>
          current.map((row) => {
            const target = selectedIds.size > 0 ? selectedIds.has(row.local_id) : row.is_enabled;
            return target
              ? {
                  ...row,
                  provider_key: voice.provider_key,
                  provider_voice_id: voice.provider_voice_id,
                  params: defaults,
                }
              : row;
          }),
        );
      }
    },
    [pickerTarget, selectedIds, updateRow, updateRows, voiceParameterSchemas],
  );

  const onProjectChange = useCallback(
    (projectKey: string) => {
      setActiveProjectKey(projectKey);
      onSelectProject(projectKey);
      setMasterArtifactUrl(null);
    },
    [onSelectProject],
  );

  return (
    <>
      <div className="page-grid script-editor-layout">
        <Panel
          title={copy.title}
          description={copy.description}
          actions={
            <div className="actions-row">
              {isDirty ? <span className="status-tag status-tag-queued">{copy.dirty}</span> : null}
              <button
                type="button"
                className="ghost-button compact-button"
                onClick={() => void saveRows()}
                disabled={isSaving}
              >
                {isSaving ? copy.saving : copy.saveRows}
              </button>
            </div>
          }
        >
          <div className="script-editor-toolbar">
            <div className="form-field compact">
              <label>{copy.project}</label>
              <select value={activeProjectKey} onChange={(event) => onProjectChange(event.target.value)}>
                {projects.map((item) => (
                  <option key={item.project_key} value={item.project_key}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="script-stats-grid">
              <div>
                <span>{copy.rows}</span>
                <strong>{stats.total}</strong>
              </div>
              <div>
                <span>{copy.activeRows}</span>
                <strong>{stats.active}</strong>
              </div>
              <div>
                <span>{copy.completedRows}</span>
                <strong>{stats.completed}</strong>
              </div>
              <div>
                <span>{copy.selectedRows}</span>
                <strong>{stats.selected}</strong>
              </div>
            </div>
          </div>

          {message ? <div className="success-banner">{message}</div> : null}
          {error ? <div className="inline-alert">{error}</div> : null}

          <div className="script-action-bar">
            <button type="button" className="ghost-button compact-button" onClick={addRow}>
              {copy.addRow}
            </button>
            <button
              type="button"
              className="ghost-button compact-button"
              onClick={() => setBulkImportOpen(true)}
            >
              {copy.bulkImport}
            </button>
            <button
              type="button"
              className="ghost-button compact-button"
              onClick={() => void downloadZip()}
              disabled={completedCount === 0}
              title={completedCount === 0 ? copy.downloadZipEmpty : undefined}
            >
              {copy.downloadZip}
            </button>
            <button
              type="button"
              className="ghost-button compact-button"
              onClick={() => setPickerTarget({ mode: "bulk" })}
            >
              {copy.bulkVoice}
            </button>
            <button
              type="button"
              className="ghost-button compact-button"
              disabled={selectedIds.size === 0}
              onClick={duplicateSelected}
            >
              {copy.duplicateSelected}
            </button>
            <button
              type="button"
              className="ghost-button compact-button danger-button"
              disabled={selectedIds.size === 0}
              onClick={deleteSelected}
            >
              {copy.deleteSelected}
            </button>
            <button
              type="button"
              className="ghost-button compact-button"
              onClick={() => void queueRows("selected")}
              disabled={selectedIds.size === 0}
            >
              {copy.queueSelected}
            </button>
            <button
              type="button"
              className="primary-button compact-primary"
              onClick={() => void queueRows("enabled")}
            >
              {copy.queueEnabled}
            </button>
          </div>
          <p className="muted-copy compact-copy">{copy.applyVoiceHint}</p>

          <div className="script-table-wrap">
            {isLoading ? <p className="muted-copy">Loading…</p> : null}
            {!isLoading && rows.length === 0 ? (
              <div className="empty-state-box">
                <p className="muted-copy">{copy.noRows}</p>
              </div>
            ) : null}
            {rows.length > 0 ? (
              <table className="script-table">
                <thead>
                  <tr>
                    <th></th>
                    <th>{copy.line}</th>
                    <th>{copy.titleField}</th>
                    <th>{copy.text}</th>
                    <th>{copy.voice}</th>
                    <th>{copy.format}</th>
                    <th>{copy.enabled}</th>
                    <th>{copy.join}</th>
                    <th>{copy.status}</th>
                    <th>{copy.output}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => {
                    const voice = voiceMap.get(buildVoiceKey(row.provider_key, row.provider_voice_id));
                    const artifactHref = row.last_artifact_download_url
                      ? artifactUrl(row.last_artifact_download_url)
                      : null;
                    return (
                      <tr
                        key={row.local_id}
                        className={`${!row.is_enabled ? "script-row-disabled" : ""} ${
                          draggedRowId === row.local_id ? "script-row-dragging" : ""
                        }`}
                        draggable
                        onDragStart={(event) => {
                          setDraggedRowId(row.local_id);
                          event.dataTransfer.effectAllowed = "move";
                          event.dataTransfer.setData("text/plain", row.local_id);
                        }}
                        onDragOver={(event) => {
                          if (draggedRowId && draggedRowId !== row.local_id) {
                            event.preventDefault();
                            event.dataTransfer.dropEffect = "move";
                          }
                        }}
                        onDrop={(event) => {
                          event.preventDefault();
                          const sourceId = event.dataTransfer.getData("text/plain") || draggedRowId;
                          if (sourceId && sourceId !== row.local_id) {
                            moveRowToIndex(sourceId, index);
                          }
                          setDraggedRowId(null);
                        }}
                        onDragEnd={() => setDraggedRowId(null)}
                      >
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedIds.has(row.local_id)}
                            onChange={() => toggleSelection(row.local_id)}
                          />
                        </td>
                        <td className="script-line-cell">
                          <strong>{index + 1}</strong>
                          <div className="reorder-buttons">
                            <button
                              type="button"
                              className="icon-button"
                              title={copy.reorderUp}
                              onClick={() => moveRow(row.local_id, -1)}
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              className="icon-button"
                              title={copy.reorderDown}
                              onClick={() => moveRow(row.local_id, 1)}
                            >
                              ↓
                            </button>
                          </div>
                        </td>
                        <td>
                          <input
                            value={row.title}
                            onChange={(event) => updateRow(row.local_id, { title: event.target.value })}
                            placeholder={`Line ${index + 1}`}
                          />
                          <input
                            value={row.speaker_label}
                            onChange={(event) =>
                              updateRow(row.local_id, { speaker_label: event.target.value })
                            }
                            placeholder={copy.speakerPlaceholder}
                            style={{ marginTop: "0.25rem" }}
                          />
                        </td>
                        <td className="script-text-cell">
                          <textarea
                            value={row.source_text}
                            rows={3}
                            onChange={(event) => updateRow(row.local_id, { source_text: event.target.value })}
                          />
                          {row.error_message ? <p className="row-error">{row.error_message}</p> : null}
                        </td>
                        <td className="script-voice-cell">
                          {voice ? (
                            <div className="row-voice-summary">
                              <VoiceAvatar voice={voice} size="sm" />
                              <div>
                                <strong>{voice.display_name}</strong>
                                <span>{voice.provider_label}</span>
                              </div>
                            </div>
                          ) : (
                            <span className="muted-copy">
                              {row.provider_voice_id ? row.provider_voice_id : copy.noVoice}
                            </span>
                          )}
                          <button
                            type="button"
                            className="ghost-button compact-button"
                            onClick={() => setPickerTarget({ mode: "row", localId: row.local_id })}
                          >
                            {copy.chooseVoice}
                          </button>
                          <details className="row-param-details">
                            <summary>Voice settings</summary>
                            <VoiceParameterPanel
                              providerKey={row.provider_key}
                              schemas={voiceParameterSchemas}
                              values={row.params ?? {}}
                              compact
                              onChange={(key, value) => updateRowParam(row.local_id, key, value)}
                            />
                          </details>
                        </td>
                        <td>
                          <select
                            value={row.output_format}
                            onChange={(event) =>
                              updateRow(row.local_id, { output_format: event.target.value })
                            }
                          >
                            <option value="">
                              {project?.default_output_format
                                ? `${copy.inherit} (${project.default_output_format})`
                                : copy.inherit}
                            </option>
                            <option value="mp3">mp3</option>
                            <option value="wav">wav</option>
                          </select>
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            checked={row.is_enabled}
                            onChange={(event) =>
                              updateRow(row.local_id, { is_enabled: event.target.checked })
                            }
                          />
                        </td>
                        <td>
                          <input
                            type="checkbox"
                            checked={row.join_to_master}
                            onChange={(event) =>
                              updateRow(row.local_id, { join_to_master: event.target.checked })
                            }
                          />
                        </td>
                        <td>
                          <StatusBadge value={row.status} />
                          {row.duration_seconds != null ? (
                            <small className="muted-copy block-copy">
                              {formatJobDuration(row.duration_seconds)}
                            </small>
                          ) : null}
                        </td>
                        <td>
                          {artifactHref ? (
                            <div className="script-output-stack">
                              <audio controls src={artifactHref} />
                              <a className="primary-link" href={artifactHref} download>
                                {copy.download}
                              </a>
                            </div>
                          ) : (
                            <span className="muted-copy">{copy.previewUnavailable}</span>
                          )}
                          {row.provider_key && row.provider_voice_id && row.source_text.trim() ? (
                            <div className="script-output-stack" style={{ marginTop: "0.4rem" }}>
                              <button
                                type="button"
                                className="ghost-button compact-button"
                                onClick={() => void handlePreviewRow(row)}
                                disabled={previewBusyId === row.local_id}
                              >
                                {previewBusyId === row.local_id ? copy.previewing : copy.preview}
                              </button>
                              {previewBlobUrls[row.local_id] ? (
                                <audio controls src={previewBlobUrls[row.local_id]} />
                              ) : null}
                              {previewErrors[row.local_id] ? (
                                <small className="muted-copy block-copy">
                                  {copy.previewError}: {previewErrors[row.local_id]}
                                </small>
                              ) : null}
                            </div>
                          ) : null}
                        </td>
                        <td>
                          {!row.provider_key || !row.provider_voice_id ? (
                            <span className="status-tag status-tag-failed">{copy.missingVoice}</span>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : null}
          </div>
        </Panel>

        <aside className="script-side-stack">
          <Panel title={copy.importTitle} description={copy.importDescription}>
            <div className="form-field">
              <textarea
                rows={8}
                value={importText}
                onChange={(event) => setImportText(event.target.value)}
                placeholder={copy.importPlaceholder}
              />
            </div>
            <button type="button" className="ghost-button" onClick={importRows} disabled={!importText.trim()}>
              {copy.splitLines}
            </button>
          </Panel>

          <Panel title={copy.mergeCompleted} description={`${copy.completedRows}: ${stats.completed}`}>
            <div className="filter-inline-grid">
              <div className="form-field compact">
                <label>{copy.mergeFormat}</label>
                <select value={mergeFormat} onChange={(event) => setMergeFormat(event.target.value)}>
                  <option value="wav">wav</option>
                  <option value="mp3">mp3</option>
                </select>
              </div>
              <div className="form-field compact">
                <label>{copy.silence}</label>
                <input
                  type="number"
                  min={0}
                  value={mergeSilenceMs}
                  onChange={(event) => setMergeSilenceMs(Number(event.target.value))}
                />
              </div>
            </div>
            <div className="script-action-column">
              <button type="button" className="primary-button" onClick={() => void mergeRows()}>
                {copy.mergeCompleted}
              </button>
              <button type="button" className="ghost-button" onClick={() => void exportProject()}>
                {copy.exportProject}
              </button>
              <button
                type="button"
                className="ghost-button compact-button"
                onClick={() => void downloadSubtitles("srt")}
              >
                {copy.downloadSubtitles} (.srt)
              </button>
              <button
                type="button"
                className="ghost-button compact-button"
                onClick={() => void downloadSubtitles("vtt")}
              >
                {copy.downloadSubtitles} (.vtt)
              </button>
            </div>
            {masterArtifactUrl ? (
              <div className="master-artifact-card">
                <strong>{copy.masterReady}</strong>
                <audio controls src={masterArtifactUrl} />
                <a className="primary-link" href={masterArtifactUrl} download>
                  {copy.download}
                </a>
              </div>
            ) : null}
          </Panel>
        </aside>
      </div>

      <VoicePickerDialog
        open={pickerTarget !== null}
        providers={providers}
        voices={voices}
        selectedVoice={selectedVoiceForPicker}
        onClose={() => setPickerTarget(null)}
        onSelectVoice={handleVoiceSelected}
      />

      <BulkImportDialog
        open={bulkImportOpen}
        projectKey={activeProjectKey}
        onClose={() => setBulkImportOpen(false)}
        onImported={(response) => {
          setMessage(`+${response.inserted}`);
          void loadRows(activeProjectKey, true);
        }}
      />
    </>
  );
});
