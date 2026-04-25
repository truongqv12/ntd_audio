import math
import struct
import wave
from io import BytesIO


def generate_tone_wav_bytes(duration_seconds: float = 1.5, frequency_hz: int = 440, sample_rate: int = 24000) -> bytes:
    total_samples = int(duration_seconds * sample_rate)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(total_samples):
            amplitude = int(32767.0 * 0.2 * math.sin(2.0 * math.pi * frequency_hz * index / sample_rate))
            wav_file.writeframesraw(struct.pack("<h", amplitude))
    return buffer.getvalue()
