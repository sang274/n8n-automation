#!/usr/bin/env python3
"""
Audio preprocessing pipeline:
1. Separate vocals/background with Demucs
2. Detect human speech in vocals with Silero VAD
3. Save a full-length human-speech track (silence outside speech)
4. Save the background (non-human) track
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

import torch
import torchaudio.functional as F
import soundfile as sf
from silero_vad import load_silero_vad, get_speech_timestamps

# ---------------------------------------------------------------- config ---
SAMPLING_RATE = 16000

VAD_THRESHOLD = 0.5
MIN_SPEECH_MS = 250
MIN_SILENCE_MS = 300
SPEECH_PAD_MS = 200

DEMUCS_MODEL = "htdemucs"
DEVICE = "cpu"

BASE_DIR = "/data/files"
OUTPUT_DIR = os.path.join(BASE_DIR, "preprocess")


# ---------------------------------------------------------------- demucs ---
def separate_audio(audio_path: str) -> tuple[str, str]:
    """Run Demucs 2-stem separation. Returns (vocals_path, no_vocals_path)."""
    audio_path = os.path.abspath(audio_path)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",
        "-n", DEMUCS_MODEL,
        "-d", DEVICE,
        "-o", OUTPUT_DIR,
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log_path = os.path.join(OUTPUT_DIR, "demucs_error.log")
        with open(log_path, "w") as f:
            f.write(f"--- STDOUT ---\n{result.stdout}\n--- STDERR ---\n{result.stderr}")
        tail = "\n".join((result.stderr or "").strip().splitlines()[-15:])
        raise RuntimeError(f"Demucs failed (code {result.returncode}). Log: {log_path}\n\n{tail}")

    demucs_dir = os.path.join(OUTPUT_DIR, DEMUCS_MODEL, Path(audio_path).stem)
    vocals_path = os.path.join(demucs_dir, "vocals.wav")
    no_vocals_path = os.path.join(demucs_dir, "no_vocals.wav")

    for path in (vocals_path, no_vocals_path):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Expected Demucs output missing:\n{path}")

    return vocals_path, no_vocals_path


# ------------------------------------------------------------------ VAD ---
def load_for_vad(path: str) -> torch.Tensor:
    """Load audio as mono float32 at SAMPLING_RATE for Silero VAD."""
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    audio = torch.from_numpy(data).mean(dim=1)  # -> mono

    if sr != SAMPLING_RATE:
        audio = F.resample(audio, sr, SAMPLING_RATE)

    return audio


def extract_speech(vocals_path: str):
    """Detect speech segments in the vocal stem. Returns (audio, timestamps)."""
    audio = load_for_vad(vocals_path)
    model = load_silero_vad()

    timestamps = get_speech_timestamps(
        audio, model,
        sampling_rate=SAMPLING_RATE,
        threshold=VAD_THRESHOLD,
        min_speech_duration_ms=MIN_SPEECH_MS,
        min_silence_duration_ms=MIN_SILENCE_MS,
        speech_pad_ms=SPEECH_PAD_MS,
    )

    if not timestamps:
        raise RuntimeError("No human speech detected.")

    return audio, timestamps


def build_full_length_speech(audio: torch.Tensor, timestamps: list) -> torch.Tensor:
    """Keep original timeline; zero out everything except speech segments."""
    output = torch.zeros_like(audio)
    for ts in timestamps:
        output[ts["start"]:ts["end"]] = audio[ts["start"]:ts["end"]]
    return output


# --------------------------------------------------------------- saving ---
def save_human_audio(audio: torch.Tensor, output_path: str):
    sf.write(output_path, audio.detach().cpu().numpy(), SAMPLING_RATE)


def save_non_human_audio(source_path: str, output_path: str):
    """Copy Demucs' no_vocals.wav as-is (no resampling needed)."""
    shutil.copy2(source_path, output_path)


def cleanup_demucs_output(vocals_path: str, no_vocals_path: str):
    """Remove temporary per-file Demucs directory (and model dir if empty)."""
    audio_dir = os.path.dirname(vocals_path)
    if os.path.isdir(audio_dir):
        shutil.rmtree(audio_dir)

    model_dir = os.path.dirname(audio_dir)
    if os.path.isdir(model_dir) and not os.listdir(model_dir):
        os.rmdir(model_dir)


# ------------------------------------------------------------------ main ---
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 preprocess.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    audio_path = os.path.join(BASE_DIR, filename)

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found:\n{audio_path}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stem = Path(filename).stem
    human_output_path = os.path.join(OUTPUT_DIR, f"{stem}_human.wav")
    non_human_output_path = os.path.join(OUTPUT_DIR, f"{stem}_non_human.wav")

    print("=== Demucs separation ===")
    vocals_path, no_vocals_path = separate_audio(audio_path)

    try:
        print("=== Detecting human speech ===")
        audio, timestamps = extract_speech(vocals_path)

        print("=== Building human speech track ===")
        human_audio = build_full_length_speech(audio, timestamps)
        save_human_audio(human_audio, human_output_path)

        print("=== Saving non-human audio ===")
        save_non_human_audio(no_vocals_path, non_human_output_path)

        speech_samples = sum(ts["end"] - ts["start"] for ts in timestamps)
        ratio = speech_samples / len(audio) * 100 if len(audio) else 0

        print("\n=== PREPROCESS COMPLETE ===")
        print(f"segments={len(timestamps)}")
        print(f"human_retained={ratio:.1f}%")
        print(f"HUMAN_OUTPUT={human_output_path}")
        print(f"NON_HUMAN_OUTPUT={non_human_output_path}")

    finally:
        print("=== Cleaning temporary Demucs files ===")
        cleanup_demucs_output(vocals_path, no_vocals_path)


if __name__ == "__main__":
    main()