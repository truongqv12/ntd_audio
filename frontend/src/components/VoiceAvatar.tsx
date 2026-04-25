import { memo } from "react";
import type { VoiceCatalogEntry } from "../types";
import { getVoiceAvatarUrl, getVoiceInitials } from "../lib/voice";

export const VoiceAvatar = memo(function VoiceAvatar({
  voice,
  size = "md",
}: {
  voice: VoiceCatalogEntry;
  size?: "sm" | "md" | "lg";
}) {
  const url = getVoiceAvatarUrl(voice);
  const initials = getVoiceInitials(voice);
  return url ? (
    <img className={`voice-avatar voice-avatar-${size}`} src={url} alt={voice.display_name} loading="lazy" />
  ) : (
    <div className={`voice-avatar voice-avatar-${size} voice-avatar-fallback`} aria-hidden="true">
      {initials}
    </div>
  );
});
