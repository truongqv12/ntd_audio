export type ProviderParamField = {
  key: string;
  label: string;
  kind: "number" | "text" | "textarea" | "boolean" | "select";
  default?: string | number | boolean | null;
  min?: number | null;
  max?: number | null;
  step?: number | null;
  unit?: string | null;
  description?: string | null;
  options: Array<{ label: string; value: string }>;
  advanced: boolean;
};

export type ProviderCredential = {
  provider_key: string;
  label: string;
  category: string;
  fields: Record<
    string,
    { label: string; secret: boolean; value: string; env?: string; env_present?: boolean }
  >;
  effective_fields: Record<string, string>;
  configured: boolean;
  env_overrides: string[];
};

export type SettingsOverview = {
  provider_credentials: ProviderCredential[];
  voice_parameter_schemas: Record<string, ProviderParamField[]>;
  merge_defaults: Record<string, unknown>;
};

export type ProviderCapabilities = {
  batch_generation: boolean;
  realtime_generation: boolean;
  local_inference: boolean;
  cloud_api: boolean;
  custom_voice: boolean;
  voice_cloning: boolean;
  expressive_speech: boolean;
  multilingual: boolean;
  requires_gpu: boolean;
  supports_preview_audio: boolean;
};

export type ProviderSummary = {
  key: string;
  label: string;
  category: string;
  configured: boolean;
  reachable: boolean;
  reason: string;
  capabilities: ProviderCapabilities;
  concurrency_limit: number;
};

export type VoiceCatalogEntry = {
  provider_key: string;
  provider_label: string;
  provider_category: string;
  provider_voice_id: string;
  display_name: string;
  locale?: string | null;
  language?: string | null;
  gender?: string | null;
  voice_type?: string | null;
  description?: string | null;
  accent?: string | null;
  age?: string | null;
  styles: string[];
  tags: string[];
  preview_url?: string | null;
  capabilities: ProviderCapabilities;
  provider_metadata: Record<string, unknown>;
};

export type CatalogResponse = {
  refreshed_at: string;
  providers: ProviderSummary[];
  voices: VoiceCatalogEntry[];
  filters: {
    providers: string[];
    languages: string[];
    voice_types: string[];
    tags: string[];
  };
};

export type VoiceSearchResponse = {
  items: VoiceCatalogEntry[];
  total: number;
  query: string;
};

export type Artifact = {
  artifact_kind: string;
  mime_type: string;
  relative_path: string;
  download_url: string;
};

export type JobEvent = {
  event_type: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type Job = {
  id: string;
  project_key: string;
  project_name?: string | null;
  provider_key: string;
  provider_voice_id: string;
  status: string;
  source_text: string;
  output_format: string;
  normalized_params: Record<string, unknown>;
  duration_seconds?: number | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  artifact?: Artifact | null;
  events: JobEvent[];
};

export type ProjectStats = {
  total_jobs: number;
  queued_jobs: number;
  running_jobs: number;
  succeeded_jobs: number;
  failed_jobs: number;
  last_job_created_at?: string | null;
};

export type Project = {
  id: string;
  project_key: string;
  name: string;
  description?: string | null;
  status: string;
  default_provider_key?: string | null;
  default_output_format: string;
  tags: string[];
  settings: Record<string, unknown>;
  is_default: boolean;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
  stats: ProjectStats;
};

export type ProjectsResponse = {
  items: Project[];
};

export type ProjectScriptRow = {
  id: string;
  project_key: string;
  row_index: number;
  title?: string | null;
  source_text: string;
  provider_key?: string | null;
  provider_voice_id?: string | null;
  output_format?: string | null;
  params: Record<string, unknown>;
  is_enabled: boolean;
  join_to_master: boolean;
  status: string;
  last_job_id?: string | null;
  last_artifact_download_url?: string | null;
  duration_seconds?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectBatchQueueResponse = {
  queued_jobs: Job[];
  merge_requested: boolean;
};

export type ProjectMergeResponse = {
  project_key: string;
  merged_count: number;
  output_format: string;
  download_url: string;
  artifact_kind: string;
};

export type BulkImportResponse = {
  project_key: string;
  inserted: number;
  rows: ProjectScriptRow[];
  queued_jobs: Job[];
};

export type HealthResponse = {
  status: string;
  providers: Record<
    string,
    {
      reachable: boolean;
      reason: string;
      configured: boolean;
    }
  >;
};

export type LiveSnapshot = {
  generated_at: string;
  jobs: Job[];
  events: JobEvent[];
  project_stats: Project[];
};

export type ProviderDiagnostic = {
  key: string;
  label: string;
  category: string;
  configured: boolean;
  reachable: boolean;
  reason: string;
  latency_ms?: number | null;
  checked_at: string;
  voice_count: number;
  active_jobs: number;
  service_target?: string | null;
  capabilities: ProviderCapabilities;
};

export type QueueMetrics = {
  queued_jobs: number;
  running_jobs: number;
  failed_jobs: number;
  succeeded_jobs: number;
  total_jobs: number;
};

export type MonitorStatus = {
  app_name: string;
  checked_at: string;
  uptime_seconds: number;
  queue: QueueMetrics;
  providers: ProviderDiagnostic[];
  guidance: string[];
};

export type LogSource = {
  key: string;
  label: string;
  source_type: string;
  available: boolean;
  description: string;
};

export type LogTail = {
  source: string;
  source_label: string;
  source_type: string;
  file_path?: string | null;
  lines: string[];
};
