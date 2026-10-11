
import sys
import subprocess
import shutil
from pathlib import Path

def process_audio(input_file_path):
    input_path = Path(input_file_path)
    if not input_path.exists():
        print(f"❌ LỖI: Không tìm thấy file {input_path}")
        sys.exit(1)
        
    work_dir = input_path.parent
    preprocess_dir = Path("/data/files/preprocess")
    
    command = [
        "python3", "-m", "demucs",
        "--two-stems=vocals",
        "-n", "htdemucs",
        "-o", str(work_dir),
        str(input_path)
    ]
    
    try:
        # Ẩn bớt log rác của Demucs để stdout được sạch sẽ
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        demucs_out_dir = work_dir / "htdemucs" / input_path.stem
        bgm_file = demucs_out_dir / "no_vocals.wav"
        vocal_file = demucs_out_dir / "vocals.wav"
        
        if bgm_file.exists():
            # 🌟 MỚI: Lưu đúng tên file và đúng thư mục mà Node Execute Command của bạn yêu cầu
            final_bgm = preprocess_dir / "vocals_non_human.wav"
            final_vocal = preprocess_dir / "vocals_human.wav"
            
            shutil.copy2(bgm_file, final_bgm)
            shutil.copy2(vocal_file, final_vocal)
            
            # 🌟 MỚI: In ra chính xác chuẩn Regex mà Node "Take Background voice" đang tìm kiếm
            print(f"NON_HUMAN_OUTPUT={final_bgm}")
            
            shutil.rmtree(work_dir / "htdemucs", ignore_errors=True)
            
    except subprocess.CalledProcessError:
        print(f"❌ LỖI: Quá trình tách AI thất bại")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    process_audio(sys.argv[1])
