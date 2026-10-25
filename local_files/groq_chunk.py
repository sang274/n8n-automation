
import os
import sys
import json
import subprocess
import glob

# Đảm bảo có thư viện requests
try:
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "--break-system-packages"], check=True)
    import requests

API_KEY = "api_key_here"  # Thay bằng API key thực tế của bạn
AUDIO_FILE = "/data/files/preprocess/vocals_human.mp3"
CHUNK_DURATION = 120 # Cắt nhỏ mỗi 2 phút (để Groq không bị quá tải)
OUTPUT_DIR = "/data/files/chunks"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Dọn dẹp chunk cũ
for f in glob.glob(f"{OUTPUT_DIR}/chunk_*.mp3"):
    try: os.remove(f)
    except: pass

# Dùng FFmpeg băm file MP3 thành nhiều file nhỏ 2 phút
try:
    subprocess.run(f'ffmpeg -y -i "{AUDIO_FILE}" -f segment -segment_time {CHUNK_DURATION} -c copy "{OUTPUT_DIR}/chunk_%03d.mp3"', shell=True, check=True, stderr=subprocess.DEVNULL)
except Exception as e:
    print(json.dumps({"error": f"Lỗi cắt file: {str(e)}"}))
    sys.exit(1)

chunks = sorted(glob.glob(f"{OUTPUT_DIR}/chunk_*.mp3"))

final_text = ""
final_segments = []
time_offset = 0.0  # Bộ đếm cộng dồn thời gian

# Gửi từng mảnh lên Groq và khâu lại
for chunk in chunks:
    with open(chunk, "rb") as f:
        files = {"file": (os.path.basename(chunk), f, "audio/mpeg")}
        data = {"model": "whisper-large-v3", "response_format": "verbose_json"}
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        try:
            res = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data)
            
            if res.status_code == 200:
                result = res.json()
                chunk_duration = result.get("duration", 0.0)
                
                final_text += result.get("text", "") + " "
                
                # Khâu mốc thời gian: Cộng dồn thời gian của các đoạn trước vào đoạn hiện tại
                for seg in result.get("segments", []):
                    seg["start"] += time_offset
                    seg["end"] += time_offset
                    seg["id"] = len(final_segments)
                    final_segments.append(seg)
                
                time_offset += chunk_duration # Cập nhật mốc thời gian cho chunk tiếp theo
                
            else:
                print(json.dumps({"error": f"Groq API Error: {res.text}"}))
                sys.exit(1)
        except Exception as e:
            print(json.dumps({"error": f"Request Failed: {str(e)}"}))
            sys.exit(1)

# Đóng gói xuất ra định dạng y hệt như Node HTTP gốc của bạn
output = {
    "task": "transcribe",
    "language": "Chinese",
    "duration": time_offset,
    "text": final_text.strip(),
    "segments": final_segments
}

print(json.dumps(output, ensure_ascii=False))
