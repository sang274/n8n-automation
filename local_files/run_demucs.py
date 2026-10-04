
import os, subprocess, shutil
try:
    import demucs
except ImportError:
    subprocess.run("pip install demucs --break-system-packages", shell=True)

audio_path = "/data/files/audio_goc.mp3"
out_dir = "/data/files/demucs_out"
os.makedirs(out_dir, exist_ok=True)

print("Đang phân giải sóng âm...")
subprocess.run(f'demucs -n htdemucs --two-stems=vocals -o "{out_dir}" "{audio_path}"', shell=True, check=True)

# Di chuyển file ra ngoài cho dễ lấy
base_path = os.path.join(out_dir, "htdemucs", "audio_goc")
if os.path.exists(os.path.join(base_path, "vocals.wav")):
    shutil.copy(os.path.join(base_path, "vocals.wav"), "/data/files/vocals.wav")
    shutil.copy(os.path.join(base_path, "no_vocals.wav"), "/data/files/no_vocals.wav")
