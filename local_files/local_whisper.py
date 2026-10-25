
import os
import sys
import json
import subprocess

# BẢO VỆ 1: Tự động cài đặt faster-whisper vào hệ thống n8n nếu chưa có
try:
    from faster_whisper import WhisperModel
except ImportError:
    # Cài đặt âm thầm, không in log rác ra làm hỏng JSON của n8n
    subprocess.run([sys.executable, "-m", "pip", "install", "faster-whisper", "--break-system-packages"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    from faster_whisper import WhisperModel

AUDIO_FILE = "/data/files/vocals_human.mp3"

if not os.path.exists(AUDIO_FILE):
    print(json.dumps({"error": f"Không tìm thấy file âm thanh tại: {AUDIO_FILE}"}))
    sys.exit(1)

# THIẾT LẬP MÔ HÌNH: 
# Chọn 'large-v3' (thông minh nhất).
# device="cpu", compute_type="int8" giúp giảm tải một nửa lượng RAM
try:
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
except Exception as e:
    print(json.dumps({"error": f"Lỗi khởi tạo mô hình: {str(e)}"}))
    sys.exit(1)

final_text = ""
final_segments = []

try:
    segments, info = model.transcribe(AUDIO_FILE, beam_size=5, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
    
    for segment in segments:
        final_text += segment.text.strip() + " "
        final_segments.append({
            "id": segment.id,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip()
        })
        
except Exception as e:
    print(json.dumps({"error": f"Lỗi trong quá trình nhận diện: {str(e)}"}))
    sys.exit(1)

output = {
    "task": "transcribe",
    "language": info.language,
    "duration": info.duration,
    "text": final_text.strip(),
    "segments": final_segments
}

print(json.dumps(output, ensure_ascii=False))
