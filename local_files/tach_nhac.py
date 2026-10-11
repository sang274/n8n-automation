import sys
import subprocess
import shutil
from pathlib import Path

def process_audio(input_file_path):
    input_path = Path(input_file_path)
    
    if not input_path.exists():
        print(f"❌ LỖI: Không tìm thấy file {input_path}")
        sys.exit(1)
        
    print(f"⏳ Đang tách thoại cho file: {input_path.name}...")
    
    # Lấy thư mục cha của file đầu vào để làm nơi xuất file tạm
    work_dir = input_path.parent
    
    # Lệnh gọi Demucs (Chạy bằng CPU trong môi trường Docker n8n)
    command = [
        "python3", "-m", "demucs",
        "--two-stems=vocals",
        "-n", "htdemucs",
        "-o", str(work_dir),
        str(input_path)
    ]
    
    try:
        # Chạy tiến trình tách âm thanh
        subprocess.run(command, check=True)
        
        # Đường dẫn mặc định mà Demucs sinh ra
        demucs_out_dir = work_dir / "htdemucs" / input_path.stem
        bgm_file = demucs_out_dir / "no_vocals.wav"
        vocal_file = demucs_out_dir / "vocals.wav"
        
        if bgm_file.exists():
            # Đổi tên và đưa ra ngoài cùng thư mục với file gốc
            final_bgm = work_dir / f"{input_path.stem}_NhanNen.wav"
            final_vocal = work_dir / f"{input_path.stem}_GiongNoi.wav"
            
            shutil.copy2(bgm_file, final_bgm)
            shutil.copy2(vocal_file, final_vocal)
            
            print(f"✅ Hoàn tất! Đã lưu file nhạc nền: {final_bgm.name}")
            
            # Dọn dẹp thư mục rác do Demucs tạo ra
            shutil.rmtree(work_dir / "htdemucs", ignore_errors=True)
            
    except subprocess.CalledProcessError:
        print(f"❌ LỖI: Quá trình tách AI thất bại cho file {input_path.name}")
        sys.exit(1)

if __name__ == "__main__":
    # Nhận đường dẫn file từ Node Execute Command của n8n truyền vào
    if len(sys.argv) < 2:
        print("❌ LỖI: Vui lòng cung cấp đường dẫn file MP3/WAV cần tách.")
        sys.exit(1)
        
    target_file = sys.argv[1]
    process_audio(target_file)