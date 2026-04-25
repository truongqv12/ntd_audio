import type { ProviderCapabilities, VoiceCatalogEntry } from "../types";

export function capabilityBadges(caps: ProviderCapabilities) {
  const items: string[] = [];
  if (caps.local_inference) items.push("local");
  if (caps.cloud_api) items.push("cloud");
  if (caps.multilingual) items.push("multilingual");
  if (caps.expressive_speech) items.push("expressive");
  if (caps.voice_cloning) items.push("cloning");
  if (caps.realtime_generation) items.push("realtime");
  if (caps.requires_gpu) items.push("gpu");
  return items;
}

export function buildVoiceSearchText(voice: VoiceCatalogEntry) {
  return [
    voice.display_name,
    voice.provider_label,
    voice.language ?? "",
    voice.locale ?? "",
    voice.voice_type ?? "",
    voice.description ?? "",
    ...(voice.tags ?? []),
    ...(voice.styles ?? []),
  ]
    .join(" ")
    .toLowerCase();
}

export function sortVoicesForProject(voices: VoiceCatalogEntry[], defaultProviderKey?: string | null) {
  if (!defaultProviderKey) return voices;
  return [...voices].sort((left, right) => {
    const leftBoost = left.provider_key === defaultProviderKey ? 0 : 1;
    const rightBoost = right.provider_key === defaultProviderKey ? 0 : 1;
    if (leftBoost !== rightBoost) return leftBoost - rightBoost;
    return left.display_name.localeCompare(right.display_name);
  });
}

export function getVoiceAvatarUrl(voice: VoiceCatalogEntry) {
  const metadata = voice.provider_metadata ?? {};
  const imageCandidate = [
    metadata.avatar_url,
    metadata.image_url,
    metadata.portrait,
    metadata.icon,
    metadata.photo_url,
  ].find((value) => typeof value === "string" && value.length > 0);
  return typeof imageCandidate === "string" ? imageCandidate : null;
}

export function getVoiceInitials(voice: VoiceCatalogEntry) {
  const text = voice.display_name.trim();
  if (!text) return "VF";
  const parts = text.split(/[\s/]+/).filter(Boolean);
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "").join("") || "VF";
}

export function getVoiceLocalesForProvider(voices: VoiceCatalogEntry[], providerKey: string) {
  return [...new Set(voices.filter((voice) => voice.provider_key === providerKey).map((voice) => voice.locale || voice.language || "unknown"))];
}

export function formatLocaleLabel(locale: string | null | undefined, uiLocale: string) {
  if (!locale) return uiLocale === "vi" ? "Không rõ locale" : "Unknown locale";
  const normalized = locale.replace("_", "-");
  const [languageCode, regionCode] = normalized.split("-");

  let languageLabel = languageCode;
  try {
    const displayNames = new Intl.DisplayNames([uiLocale], { type: "language" });
    languageLabel = displayNames.of(languageCode) ?? languageCode;
  } catch {
    languageLabel = languageCode;
  }

  if (!regionCode) return `${languageLabel} · ${normalized}`;

  let regionLabel = regionCode;
  try {
    const displayNames = new Intl.DisplayNames([uiLocale], { type: "region" });
    regionLabel = displayNames.of(regionCode.toUpperCase()) ?? regionCode;
  } catch {
    regionLabel = regionCode;
  }

  return `${regionLabel} · ${normalized}`;
}
