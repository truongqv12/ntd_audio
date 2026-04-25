import type {
  CatalogResponse,
  HealthResponse,
  Job,
  LiveSnapshot,
  LogSource,
  LogTail,
  MonitorStatus,
  Project,
  ProjectBatchQueueResponse,
  ProjectMergeResponse,
  ProjectScriptRow,
  ProjectsResponse,
  ProviderSummary,
  VoiceSearchResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

function authHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {};
  if (extra) {
    if (extra instanceof Headers) {
      extra.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(extra)) {
      for (const [key, value] of extra) headers[key] = value;
    } else {
      Object.assign(headers, extra as Record<string, string>);
    }
  }
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  return headers;
}

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return apiFetch(`${path}`, { ...init, headers: authHeaders(init.headers) });
}

export { API_BASE };

export async function fetchSettingsOverview(): Promise<import("./types").SettingsOverview> {
  const response = await apiFetch(`/settings`);
  if (!response.ok) throw new Error("Unable to fetch settings");
  return response.json();
}

export async function fetchVoiceParameterSchemas(): Promise<
  Record<string, import("./types").ProviderParamField[]>
> {
  const response = await apiFetch(`/settings/voice-parameter-schemas`);
  if (!response.ok) throw new Error("Unable to fetch voice parameter schemas");
  const data = await response.json();
  return data.schemas;
}

export async function updateProviderCredentials(
  providerKey: string,
  fields: Record<string, unknown>,
): Promise<import("./types").ProviderCredential> {
  const response = await fetch(
    `${API_BASE}/settings/provider-credentials/${encodeURIComponent(providerKey)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields }),
    },
  );
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to update provider credentials");
  }
  return response.json();
}

export async function updateMergeDefaults(fields: Record<string, unknown>): Promise<Record<string, unknown>> {
  const response = await apiFetch(`/settings/merge-defaults`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to update merge defaults");
  }
  return response.json();
}

export async function fetchProviders(): Promise<ProviderSummary[]> {
  const response = await apiFetch(`/providers`);
  if (!response.ok) throw new Error("Unable to fetch providers");
  return response.json();
}

export async function fetchCatalog(refresh = false): Promise<CatalogResponse> {
  const response = await apiFetch(`/catalog/voices${refresh ? "?refresh=true" : ""}`);
  if (!response.ok) throw new Error("Unable to fetch voice catalog");
  return response.json();
}

export async function fetchVoiceSearch(params: {
  q?: string;
  provider_key?: string;
  language?: string;
  locale?: string;
  voice_type?: string;
  limit?: number;
}): Promise<VoiceSearchResponse> {
  const query = new URLSearchParams();
  if (params.q) query.set("q", params.q);
  if (params.provider_key) query.set("provider_key", params.provider_key);
  if (params.language) query.set("language", params.language);
  if (params.locale) query.set("locale", params.locale);
  if (params.voice_type) query.set("voice_type", params.voice_type);
  if (params.limit) query.set("limit", String(params.limit));
  const response = await apiFetch(`/catalog/voices/search?${query.toString()}`);
  if (!response.ok) throw new Error("Unable to search voice catalog");
  return response.json();
}

export interface JobsListParams {
  limit?: number;
  offset?: number;
  status?: string;
  provider_key?: string;
  project_key?: string;
  q?: string;
}

export interface JobsPage {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchJobs(params: JobsListParams = {}): Promise<JobsPage> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  if (params.status) query.set("status", params.status);
  if (params.provider_key) query.set("provider_key", params.provider_key);
  if (params.project_key) query.set("project_key", params.project_key);
  if (params.q) query.set("q", params.q);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await apiFetch(`/jobs${suffix}`);
  if (!response.ok) throw new Error("Unable to fetch jobs");
  return response.json();
}

export async function cancelJob(jobId: string): Promise<Job> {
  const response = await apiFetch(`/jobs/${jobId}/cancel`, { method: "POST" });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to cancel job");
  }
  return response.json();
}

export async function retryJob(jobId: string): Promise<Job> {
  const response = await apiFetch(`/jobs/${jobId}/retry`, { method: "POST" });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to retry job");
  }
  return response.json();
}

export async function fetchJob(jobId: string): Promise<Job> {
  const response = await apiFetch(`/jobs/${jobId}`);
  if (!response.ok) throw new Error("Unable to fetch job");
  return response.json();
}

export async function fetchProjects(): Promise<Project[]> {
  const response = await apiFetch(`/projects`);
  if (!response.ok) throw new Error("Unable to fetch projects");
  const data: ProjectsResponse = await response.json();
  return data.items;
}

export async function createProject(payload: {
  project_key: string;
  name: string;
  description?: string;
  status?: string;
  default_provider_key?: string;
  default_output_format?: string;
  tags?: string[];
  settings?: Record<string, unknown>;
  is_default?: boolean;
}): Promise<Project> {
  const response = await apiFetch(`/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to create project");
  }
  return response.json();
}

export async function updateProject(projectKey: string, payload: Record<string, unknown>): Promise<Project> {
  const response = await apiFetch(`/projects/${projectKey}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to update project");
  }
  return response.json();
}

export async function fetchProjectRows(projectKey: string): Promise<ProjectScriptRow[]> {
  const response = await apiFetch(`/projects/${projectKey}/rows`);
  if (!response.ok) throw new Error("Unable to fetch project rows");
  const data = await response.json();
  return data.items;
}

export async function replaceProjectRows(
  projectKey: string,
  rows: Array<Record<string, unknown>>,
): Promise<ProjectScriptRow[]> {
  const response = await apiFetch(`/projects/${projectKey}/rows`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to save project rows");
  }
  const data = await response.json();
  return data.items;
}

export async function queueProjectRows(
  projectKey: string,
  payload: {
    row_ids?: string[];
    merge_outputs?: boolean;
    merge_output_format?: string;
    merge_silence_ms?: number;
  },
): Promise<ProjectBatchQueueResponse> {
  const response = await apiFetch(`/projects/${projectKey}/rows/queue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to queue project rows");
  }
  return response.json();
}

export async function mergeProjectRows(
  projectKey: string,
  payload: {
    row_ids?: string[];
    merge_output_format?: string;
    merge_silence_ms?: number;
  },
): Promise<ProjectMergeResponse> {
  const response = await apiFetch(`/projects/${projectKey}/rows/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to merge project rows");
  }
  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await apiFetch(`/health`);
  if (!response.ok) throw new Error("Unable to fetch health");
  return response.json();
}

export async function fetchMonitorStatus(): Promise<MonitorStatus> {
  const response = await apiFetch(`/monitor/status`);
  if (!response.ok) throw new Error("Unable to fetch monitor status");
  return response.json();
}

export async function fetchMonitorLogSources(): Promise<LogSource[]> {
  const response = await apiFetch(`/monitor/log-sources`);
  if (!response.ok) throw new Error("Unable to fetch log sources");
  return response.json();
}

export async function fetchMonitorLogs(source = "api", limit = 200): Promise<LogTail> {
  const response = await fetch(
    `${API_BASE}/monitor/logs?source=${encodeURIComponent(source)}&limit=${limit}`,
  );
  if (!response.ok) throw new Error("Unable to fetch logs");
  return response.json();
}

export async function fetchSnapshot(): Promise<LiveSnapshot> {
  const response = await apiFetch(`/events/snapshot`);
  if (!response.ok) throw new Error("Unable to fetch snapshot");
  return response.json();
}

export async function createJob(payload: {
  project_key: string;
  provider_key: string;
  provider_voice_id: string;
  source_text: string;
  output_format: string;
  params: Record<string, unknown>;
}): Promise<Job> {
  const response = await apiFetch(`/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Unable to create job");
  }
  return response.json();
}

export function openEventStream(onSnapshot: (snapshot: LiveSnapshot) => void): EventSource {
  const url = API_KEY
    ? `${API_BASE}/events/stream?api_key=${encodeURIComponent(API_KEY)}`
    : `${API_BASE}/events/stream`;
  const source = new EventSource(url);
  source.addEventListener("snapshot", (event) => {
    const payload = JSON.parse((event as MessageEvent).data) as LiveSnapshot;
    onSnapshot(payload);
  });
  return source;
}

export function artifactUrl(relativeUrl: string): string {
  return `${API_BASE}${relativeUrl}`;
}

export function providerVoicePreviewUrl(providerKey: string, voiceId: string, text?: string): string {
  const query = text ? `?text=${encodeURIComponent(text)}` : "";
  return `${API_BASE}/providers/${encodeURIComponent(providerKey)}/voices/${encodeURIComponent(voiceId)}/preview${query}`;
}
