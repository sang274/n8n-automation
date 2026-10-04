
import sys
import wave
import json
import subprocess
import traceback
import shutil
import glob
import os
from piper import PiperVoice

def get_atempo_filter(ratio):
    # Chỉ cho phép tăng tốc (ratio > 1.0). Tuyệt đối không làm chậm (ratio < 1.0)
    if ratio <= 1.0:
        return None
    filters = []
    while ratio > 2.0:
        filters.append("atempo=2.0")
        ratio /= 2.0
    filters.append(f"atempo={ratio}")
    return ",".join(filters)

try:
    segments = json.load(open('/data/files/segments.json', 'r', encoding='utf-8'))
    voice = PiperVoice.load('/data/files/ngochuyennew.onnx', config_path='/data/files/ngochuyennew.onnx.json')
    sr = voice.config.sample_rate
    
    concat_list = []
    
    for i, seg in enumerate(segments):
        out_wav = f'/data/files/seg_{i}.wav'
        
        if seg['type'] == 'silence':
            dur = float(seg['duration'])
            if dur > 0:
                subprocess.run(f'ffmpeg -y -f lavfi -i anullsrc=r={sr}:cl=mono -t {dur} -c:a pcm_s16le {out_wav}', shell=True, stderr=subprocess.DEVNULL)
                concat_list.append(f"file '{out_wav}'")
                
        elif seg['type'] == 'speech':
            text = seg['text']
            target_dur = float(seg['duration'])
            raw_wav = f'/data/files/raw_{i}.wav'
            
            # Đọc câu thoại ra file wav thô với tốc độ tự nhiên chuẩn của model
            with wave.open(raw_wav, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sr)
                for chunk in voice.synthesize(text):
                    wav_file.writeframes(chunk.audio_int16_bytes)
            
            if target_dur > 0:
                duration_cmd = f"ffprobe -i {raw_wav} -show_entries format=duration -v quiet -of csv=p=0"
                actual_dur = float(subprocess.check_output(duration_cmd, shell=True).decode().strip())
                
                if actual_dur > 0:
                    # Nếu giọng đọc tự nhiên dài hơn thời lượng cho phép (cần ép đọc nhanh hơn)
                    if actual_dur > target_dur:
                        atempo = actual_dur / target_dur
                        filter_str = get_atempo_filter(atempo)
                        if filter_str:
                            subprocess.run(f'ffmpeg -y -i {raw_wav} -filter:a "{filter_str}" {out_wav}', shell=True, stderr=subprocess.DEVNULL)
                        else:
                            shutil.copy(raw_wav, out_wav)
                    else:
                        # GIỮ NGUYÊN TỐC ĐỘ TỰ NHIÊN (Nếu đọc xong sớm hơn target_dur)
                        shutil.copy(raw_wav, out_wav)
                        
                        # TÍNH TOÁN KHOẢNG LẶNG BÙ TRỪ: Đọc xong sớm thì im lặng chờ đến hết mốc thời gian
                        diff_dur = target_dur - actual_dur
                        if diff_dur > 0.05: # Chỉ bù nếu chênh lệch đáng kể (>50ms)
                            silence_wav = f'/data/files/silence_pad_{i}.wav'
                            subprocess.run(f'ffmpeg -y -f lavfi -i anullsrc=r={sr}:cl=mono -t {diff_dur} -c:a pcm_s16le {silence_wav}', shell=True, stderr=subprocess.DEVNULL)
                            concat_list.append(f"file '{silence_wav}'")
                else:
                    shutil.copy(raw_wav, out_wav)
            else:
                shutil.copy(raw_wav, out_wav)
                
            concat_list.append(f"file '{out_wav}'")

    concat_file = '/data/files/concat.txt'
    with open(concat_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(concat_list))
    
    print("Đang nối toàn bộ các đoạn Audio và khoảng lặng chờ...")
    subprocess.run(f'ffmpeg -y -f concat -safe 0 -i {concat_file} -codec:a libmp3lame -qscale:a 2 /data/files/audio_vi.mp3', shell=True, stderr=subprocess.DEVNULL)
    
    # Dọn dẹp rác hệ thống
    for f in glob.glob('/data/files/raw_*.wav') + glob.glob('/data/files/seg_*.wav') + glob.glob('/data/files/silence_pad_*.wav') + [concat_file]:
        try: os.remove(f)
        except: pass

except Exception as e:
    print("LỖI PYTHON CHI TIẾT:")
    traceback.print_exc()
    sys.exit(1)
