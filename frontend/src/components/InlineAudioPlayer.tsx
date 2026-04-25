import { memo } from "react";
import { artifactUrl } from "../api";

export const InlineAudioPlayer = memo(function InlineAudioPlayer({
  downloadUrl,
  mimeType,
}: {
  downloadUrl: string;
  mimeType?: string;
}) {
  return (
    <audio
      className="inline-audio-player"
      controls
      preload="none"
      src={artifactUrl(downloadUrl)}
      data-mime-type={mimeType ?? "audio/mpeg"}
    >
      <track kind="captions" />
    </audio>
  );
});
