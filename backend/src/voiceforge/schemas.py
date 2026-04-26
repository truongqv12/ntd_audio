from datetime import datetime

from pydantic import BaseModel, Field


class ProviderCapabilitiesResponse(BaseModel):
    batch_generation: bool
    realtime_generation: bool
    local_inference: bool
    cloud_api: bool
    custom_voice: bool
    voice_cloning: bool
    expressive_speech: bool
    multilingual: bool
    requires_gpu: bool
    supports_preview_audio: bool


class ProviderSummaryResponse(BaseModel):
    key: str
    label: str
    category: str
    configured: bool
    reachable: bool
    reason: str
    capabilities: ProviderCapabilitiesResponse
    concurrency_limit: int = 1


class VoiceCatalogEntryResponse(BaseModel):
    provider_key: str
    provider_label: str
    provider_category: str
    provider_voice_id: str
    display_name: str
    locale: str | None = None
    language: str | None = None
    gender: str | None = None
    voice_type: str | None = None
    description: str | None = None
    accent: str | None = None
    age: str | None = None
    styles: list[str] = []
    tags: list[str] = []
    preview_url: str | None = None
    capabilities: ProviderCapabilitiesResponse
    provider_metadata: dict = {}


class CatalogResponse(BaseModel):
    refreshed_at: datetime
    providers: list[ProviderSummaryResponse]
    voices: list[VoiceCatalogEntryResponse]
    filters: dict


class VoiceSearchResponse(BaseModel):
    items: list[VoiceCatalogEntryResponse]
    total: int
    query: str = ""


class ProjectBase(BaseModel):
    project_key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: str = "active"
    default_provider_key: str | None = None
    default_output_format: str = "mp3"
    tags: list[str] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class CreateProjectRequest(ProjectBase):
    is_default: bool = False


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    default_provider_key: str | None = None
    default_output_format: str | None = None
    tags: list[str] | None = None
    settings: dict | None = None
    is_default: bool | None = None


class ProjectStatsResponse(BaseModel):
    total_jobs: int = 0
    queued_jobs: int = 0
    running_jobs: int = 0
    succeeded_jobs: int = 0
    failed_jobs: int = 0
    last_job_created_at: datetime | None = None


class ProjectResponse(ProjectBase):
    id: str
    is_default: bool
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    stats: ProjectStatsResponse = Field(default_factory=ProjectStatsResponse)


class ProjectsResponse(BaseModel):
    items: list[ProjectResponse]


class ProjectScriptRowBase(BaseModel):
    row_index: int
    title: str | None = None
    source_text: str
    speaker_label: str | None = None
    provider_key: str | None = None
    provider_voice_id: str | None = None
    output_format: str | None = None
    params: dict = Field(default_factory=dict)
    is_enabled: bool = True
    join_to_master: bool = True


class ProjectScriptRowResponse(ProjectScriptRowBase):
    id: str
    project_key: str
    status: str
    last_job_id: str | None = None
    last_artifact_download_url: str | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectRowsResponse(BaseModel):
    items: list[ProjectScriptRowResponse]


class UpsertProjectRowsRequest(BaseModel):
    rows: list[ProjectScriptRowBase] = Field(default_factory=list)


class QueueProjectRowsRequest(BaseModel):
    row_ids: list[str] | None = None
    merge_outputs: bool = False
    merge_output_format: str = "wav"
    merge_silence_ms: int = 150


class ProjectBatchQueueResponse(BaseModel):
    queued_jobs: list["JobResponse"] = Field(default_factory=list)
    merge_requested: bool = False


class ProjectMergeResponse(BaseModel):
    project_key: str
    merged_count: int
    output_format: str
    download_url: str


class BulkImportResponse(BaseModel):
    project_key: str
    inserted: int
    rows: list[ProjectScriptRowResponse] = Field(default_factory=list)
    queued_jobs: list["JobResponse"] = Field(default_factory=list)


class CreateJobRequest(BaseModel):
    project_key: str = Field(default="default")
    provider_key: str
    provider_voice_id: str
    source_text: str
    output_format: str = "mp3"
    params: dict = Field(default_factory=dict)


class ArtifactResponse(BaseModel):
    artifact_kind: str
    mime_type: str
    relative_path: str
    download_url: str


class JobEventResponse(BaseModel):
    event_type: str
    message: str
    payload: dict
    created_at: datetime


class JobResponse(BaseModel):
    id: str
    project_key: str
    project_name: str | None = None
    provider_key: str
    provider_voice_id: str
    status: str
    source_text: str
    output_format: str
    normalized_params: dict
    duration_seconds: float | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifact: ArtifactResponse | None = None
    events: list[JobEventResponse] = []


class JobsResponse(BaseModel):
    items: list[JobResponse]
    total: int = 0
    limit: int = 50
    offset: int = 0


class LiveSnapshotResponse(BaseModel):
    generated_at: datetime
    jobs: list[JobResponse]
    events: list[JobEventResponse]
    project_stats: list[ProjectResponse]


class ProviderDiagnosticResponse(BaseModel):
    key: str
    label: str
    category: str
    configured: bool
    reachable: bool
    reason: str
    latency_ms: float | None = None
    checked_at: datetime
    voice_count: int = 0
    active_jobs: int = 0
    service_target: str | None = None
    capabilities: ProviderCapabilitiesResponse


class QueueMetricsResponse(BaseModel):
    queued_jobs: int = 0
    running_jobs: int = 0
    failed_jobs: int = 0
    succeeded_jobs: int = 0
    total_jobs: int = 0


class LogSourceResponse(BaseModel):
    key: str
    label: str
    source_type: str
    available: bool
    description: str


class LogTailResponse(BaseModel):
    source: str
    source_label: str
    source_type: str
    file_path: str | None = None
    lines: list[str]


class MonitorStatusResponse(BaseModel):
    app_name: str
    checked_at: datetime
    uptime_seconds: float
    queue: QueueMetricsResponse
    providers: list[ProviderDiagnosticResponse]
    guidance: list[str] = []


class ProviderParamFieldResponse(BaseModel):
    key: str
    label: str
    kind: str = "number"
    default: str | float | int | bool | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str | None = None
    description: str | None = None
    options: list[dict[str, str]] = Field(default_factory=list)
    advanced: bool = False


class ProviderParameterSchemasResponse(BaseModel):
    schemas: dict[str, list[ProviderParamFieldResponse]]


class ProviderCredentialResponse(BaseModel):
    provider_key: str
    label: str
    category: str
    fields: dict
    effective_fields: dict = Field(default_factory=dict)
    configured: bool = False
    env_overrides: list[str] = Field(default_factory=list)


class ProviderCredentialUpdateRequest(BaseModel):
    fields: dict = Field(default_factory=dict)


class SettingsOverviewResponse(BaseModel):
    provider_credentials: list[ProviderCredentialResponse]
    voice_parameter_schemas: dict[str, list[ProviderParamFieldResponse]]
    merge_defaults: dict = Field(default_factory=dict)
