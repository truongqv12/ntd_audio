import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  cancelJob as cancelJobApi,
  createJob,
  createProject,
  fetchCatalog,
  fetchHealth,
  fetchProjects,
  fetchSettingsOverview,
  fetchProviders,
  openEventStream,
  retryJob as retryJobApi,
  updateProject,
} from "../api";
import type {
  HealthResponse,
  Job,
  JobEvent,
  Project,
  ProviderParamField,
  ProviderSummary,
  SettingsOverview,
  VoiceCatalogEntry,
} from "../types";

const DEFAULT_SOURCE_TEXT =
  "Xin chào! Đây là VoiceForge Studio. Giao diện này ưu tiên workflow sinh voice, quản lý project, theo dõi job theo thời gian thực và lưu kết quả tập trung.";

const DEFAULT_VOICE_PARAMS: Record<string, string | number | boolean> = {
  speed: 1,
  pitch: 1,
  volume: 1,
  instructions: "",
  style_prompt: "",
  reference_audio_url: "",
  speedScale: 1,
  pitchScale: 0,
  intonationScale: 1,
  volumeScale: 1,
  length_scale: 1,
  noise_scale: 0.667,
  noise_w: 0.8,
  speakingRate: 1,
  speaking_rate: 1,
  volumeGainDb: 0,
  volume_gain_db: 0,
  stability: 0.5,
  similarity_boost: 0.75,
  style: 0,
  use_speaker_boost: true,
  rate: 0,
  sampleRateHertz: 0,
  lowLatencyJourneySynthesis: false,
};

export function useStudioController() {
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [voices, setVoices] = useState<VoiceCatalogEntry[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [liveEvents, setLiveEvents] = useState<JobEvent[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [settingsOverview, setSettingsOverview] = useState<SettingsOverview | null>(null);
  const [voiceParameterSchemas, setVoiceParameterSchemas] = useState<Record<string, ProviderParamField[]>>(
    {},
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [selectedProjectKey, setSelectedProjectKey] = useState("default");
  const [selectedVoiceKey, setSelectedVoiceKey] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [sourceText, setSourceText] = useState(DEFAULT_SOURCE_TEXT);
  const [outputFormat, setOutputFormat] = useState("mp3");
  const [voiceParams, setVoiceParams] =
    useState<Record<string, string | number | boolean>>(DEFAULT_VOICE_PARAMS);
  const [lastSeenEventAt, setLastSeenEventAt] = useState<string | null>(null);
  const bootstrapDoneRef = useRef(false);

  const bootstrap = useCallback(async (refreshCatalog = false) => {
    try {
      setErrorMessage(null);
      const [providersData, catalog, projectsData, healthData, settingsData] = await Promise.all([
        fetchProviders(),
        fetchCatalog(refreshCatalog),
        fetchProjects(),
        fetchHealth(),
        fetchSettingsOverview(),
      ]);

      setProviders(providersData);
      setVoices(catalog.voices);
      setProjects(projectsData);
      setHealth(healthData);
      setSettingsOverview(settingsData);
      setVoiceParameterSchemas(settingsData.voice_parameter_schemas ?? {});

      setSelectedVoiceKey((current) => {
        if (
          current &&
          catalog.voices.some((voice) => `${voice.provider_key}:${voice.provider_voice_id}` === current)
        ) {
          return current;
        }
        const firstVoice = catalog.voices[0];
        return firstVoice ? `${firstVoice.provider_key}:${firstVoice.provider_voice_id}` : null;
      });

      setSelectedProjectKey((current) => {
        if (projectsData.some((project) => project.project_key === current)) return current;
        const defaultProject = projectsData.find((project) => project.is_default) ?? projectsData[0];
        return defaultProject?.project_key ?? "default";
      });

      if (!bootstrapDoneRef.current) {
        bootstrapDoneRef.current = true;
        const defaultProject = projectsData.find((project) => project.is_default) ?? projectsData[0];
        if (defaultProject?.default_output_format) setOutputFormat(defaultProject.default_output_format);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Bootstrap failed");
    }
  }, []);

  useEffect(() => {
    bootstrap().catch(() => undefined);
  }, [bootstrap]);

  useEffect(() => {
    const source = openEventStream((snapshot) => {
      setJobs(snapshot.jobs);
      setLiveEvents(snapshot.events);
      setProjects(snapshot.project_stats);
      setSelectedJobId((current) => current ?? snapshot.jobs[0]?.id ?? null);
    });
    source.onerror = () => undefined;
    return () => source.close();
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_key === selectedProjectKey) ?? null,
    [projects, selectedProjectKey],
  );

  useEffect(() => {
    if (!selectedProject) return;
    if (selectedProject.default_output_format) {
      setOutputFormat((current) => current || selectedProject.default_output_format);
    }
  }, [selectedProject]);

  const selectedVoice = useMemo(() => {
    if (!selectedVoiceKey) return null;
    return (
      voices.find((voice) => `${voice.provider_key}:${voice.provider_voice_id}` === selectedVoiceKey) ?? null
    );
  }, [voices, selectedVoiceKey]);

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );

  const metrics = useMemo(
    () => ({
      totalJobs: jobs.length,
      activeJobs: jobs.filter((job) => ["queued", "running"].includes(job.status)).length,
      succeededJobs: jobs.filter((job) => job.status === "succeeded").length,
      failedJobs: jobs.filter((job) => job.status === "failed").length,
      voiceCount: voices.length,
      projectCount: projects.length,
      healthyProviders: providers.filter((provider) => provider.reachable).length,
      storedResults: jobs.filter((job) => job.artifact).length,
    }),
    [jobs, projects.length, providers, voices.length],
  );

  const unreadNotifications = useMemo(() => {
    if (!lastSeenEventAt) return liveEvents.length;
    const lastSeen = new Date(lastSeenEventAt).getTime();
    return liveEvents.filter((event) => new Date(event.created_at).getTime() > lastSeen).length;
  }, [lastSeenEventAt, liveEvents]);

  const markNotificationsSeen = useCallback(() => {
    const latest = liveEvents[liveEvents.length - 1]?.created_at ?? null;
    setLastSeenEventAt(latest);
  }, [liveEvents]);

  const setSelectedVoice = useCallback((voice: VoiceCatalogEntry | null) => {
    setSelectedVoiceKey(voice ? `${voice.provider_key}:${voice.provider_voice_id}` : null);
  }, []);

  const setSelectedJob = useCallback((job: Job | null) => {
    setSelectedJobId(job?.id ?? null);
  }, []);

  const updateVoiceParam = useCallback((key: string, value: string | number | boolean) => {
    setVoiceParams((current) => ({ ...current, [key]: value }));
  }, []);

  const createSynthesisJob = useCallback(async () => {
    if (!selectedVoice || !sourceText.trim()) return null;

    const providerKey = selectedVoice.provider_key;
    const params: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(voiceParams)) {
      if (value !== "" && value !== undefined) params[key] = value;
    }

    if (providerKey === "voicevox") {
      params.speedScale = Number(voiceParams.speedScale ?? 1);
      params.pitchScale = Number(voiceParams.pitchScale ?? 0);
      params.intonationScale = Number(voiceParams.intonationScale ?? 1);
      params.volumeScale = Number(voiceParams.volumeScale ?? 1);
    }

    if (providerKey === "piper") {
      params.length_scale = Number(voiceParams.length_scale ?? 1);
      params.noise_scale = Number(voiceParams.noise_scale ?? 0.667);
      params.noise_w = Number(voiceParams.noise_w ?? 0.8);
    }

    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const created = await createJob({
        project_key: selectedProjectKey,
        provider_key: selectedVoice.provider_key,
        provider_voice_id: selectedVoice.provider_voice_id,
        source_text: sourceText,
        output_format: outputFormat,
        params,
      });
      setSelectedJobId(created.id);
      return created;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create job");
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, [outputFormat, selectedProjectKey, selectedVoice, sourceText, voiceParams]);

  const createWorkspaceProject = useCallback(
    async (payload: {
      project_key: string;
      name: string;
      description?: string;
      default_provider_key?: string;
      default_output_format?: string;
      tags?: string[];
      settings?: Record<string, unknown>;
      is_default?: boolean;
    }) => {
      try {
        setErrorMessage(null);
        const created = await createProject(payload);
        setProjects((current) => [
          created,
          ...current.filter((item) => item.project_key !== created.project_key),
        ]);
        setSelectedProjectKey(created.project_key);
        return created;
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Unable to create project");
        return null;
      }
    },
    [],
  );

  const toggleArchiveProject = useCallback(async (project: Project) => {
    try {
      setErrorMessage(null);
      const next = await updateProject(project.project_key, {
        status: project.status === "archived" ? "active" : "archived",
      });
      setProjects((current) => current.map((item) => (item.project_key === next.project_key ? next : item)));
      return next;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update project");
      return null;
    }
  }, []);

  const cancelJobAction = useCallback(async (jobId: string) => {
    try {
      setErrorMessage(null);
      const updated = await cancelJobApi(jobId);
      setJobs((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      return updated;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to cancel job");
      return null;
    }
  }, []);

  const retryJobAction = useCallback(async (jobId: string) => {
    try {
      setErrorMessage(null);
      const newJob = await retryJobApi(jobId);
      setJobs((current) => [newJob, ...current.filter((item) => item.id !== newJob.id)]);
      setSelectedJobId(newJob.id);
      return newJob;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to retry job");
      return null;
    }
  }, []);

  const updateProjectDefaults = useCallback(async (projectKey: string, payload: Record<string, unknown>) => {
    try {
      setErrorMessage(null);
      const next = await updateProject(projectKey, payload);
      setProjects((current) => current.map((item) => (item.project_key === next.project_key ? next : item)));
      return next;
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update project");
      return null;
    }
  }, []);

  return {
    providers,
    voices,
    projects,
    jobs,
    liveEvents,
    health,
    settingsOverview,
    voiceParameterSchemas,
    errorMessage,
    setErrorMessage,
    isSubmitting,
    metrics,
    unreadNotifications,
    markNotificationsSeen,
    selectedProject,
    selectedProjectKey,
    setSelectedProjectKey,
    selectedVoice,
    setSelectedVoice,
    selectedJob,
    setSelectedJob,
    sourceText,
    setSourceText,
    outputFormat,
    setOutputFormat,
    voiceParams,
    updateVoiceParam,
    createSynthesisJob,
    createWorkspaceProject,
    toggleArchiveProject,
    updateProjectDefaults,
    cancelJob: cancelJobAction,
    retryJob: retryJobAction,
    refreshCatalog: bootstrap,
  };
}
