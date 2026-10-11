#!/usr/bin/env python3
"""
Audio preprocessing pipeline:
1. Separate vocals/background with Demucs
2. Detect human speech in vocals with Silero VAD
3. Save a full-length human-speech track
4. Save the perfect background by SUBTRACTING strictly detected speech from the original audio.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import numpy as np 

import torch
import torchaudio.functional as F
import soundfile as sf
from silero_vad import load_silero_vad, get_speech_timestamps

# ---------------------------------------------------------------- config ---
SAMPLING_RATE = 16000

# 🌟 CÁC THÔNG SỐ ĐÃ ĐƯỢC TINH CHỈNH ĐỂ KHÔNG BỊ CẮT LỐ
VAD_THRESHOLD = 0.6  # Tăng độ khó: Chắc chắn là giọng người thì mới cắt (Tránh cắt nhầm hiệu ứng)
MIN_SPEECH_MS = 100  # Bắt cả những tiếng la hét hoặc từ nói ngắn gọn
MIN_SILENCE_MS = 200
SPEECH_PAD_MS = 30   # (QUAN TRỌNG) Giảm từ 200ms xuống 30ms. Cắt bám cực sát vào viền giọng nói, giữ lại tối đa hiệu ứng môi trường!

DEMUCS_MODEL = "htdemucs"
DEVICE = "cpu"

BASE_DIR = "/data/files"
OUTPUT_DIR = os.path.join(BASE_DIR, "preprocess")


# ---------------------------------------------------------------- demucs ---
def separate_audio(audio_path: str) -> tuple[str, str]:
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
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    audio = torch.from_numpy(data).mean(dim=1)  # -> mono
    if sr != SAMPLING_RATE:
        audio = F.resample(audio, sr, SAMPLING_RATE)
    return audio


def extract_speech(vocals_path: str):
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


def cleanup_demucs_output(vocals_path: str, no_vocals_path: str):
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
        audio_16k, timestamps = extract_speech(vocals_path)

        print("=== Building high-quality tracks (Hard Cut - Lồng tiếng) ===")
        vocals_hq, sr_hq = sf.read(vocals_path)
        no_vocals_hq, _ = sf.read(no_vocals_path)

        # 1. Tái tạo Âm thanh gốc nguyên bản
        original_hq = vocals_hq + no_vocals_hq
        
        human_hq = np.zeros_like(vocals_hq)
        scale_factor = sr_hq / SAMPLING_RATE
        is_stereo = len(vocals_hq.shape) == 2

        # Làm mềm mép cắt cực nhanh (30ms) để không cắt lẹm vào hiệu ứng xung quanh
        fade_samples = int((30 / 1000.0) * sr_hq) 

        for ts in timestamps:
            start_hq = int(ts["start"] * scale_factor)
            end_hq = int(ts["end"] * scale_factor)
            
            chunk_len = end_hq - start_hq
            chunk = np.copy(vocals_hq[start_hq:end_hq])
            
            if chunk_len > fade_samples * 2:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                if is_stereo:
                    fade_in = np.expand_dims(fade_in, axis=1)
                    fade_out = np.expand_dims(fade_out, axis=1)
                
                chunk[:fade_samples] *= fade_in
                chunk[-fade_samples:] *= fade_out
                
            human_hq[start_hq:end_hq] = chunk

        # 2. XÓA SỔ GIỌNG NÓI KHỎI FILE GỐC (Phase Inversion)
        # Bất cứ âm thanh nào (chém kiếm, tiếng thở, nhạc...) không phải giọng nói sẽ được giữ lại 100%
        final_background_hq = original_hq - human_hq

        print("=== Saving output audio ===")
        sf.write(human_output_path, human_hq, sr_hq)
        sf.write(non_human_output_path, final_background_hq, sr_hq)

        speech_samples = sum(ts["end"] - ts["start"] for ts in timestamps)
        ratio = speech_samples / len(audio_16k) * 100 if len(audio_16k) else 0

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