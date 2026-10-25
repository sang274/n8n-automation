
import sys
import os
import glob
import time
import subprocess
import traceback

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    
    video_path = sys.argv[1]
    caption = sys.argv[2]
    
    # 🌟 Tìm TẤT CẢ các file có tiền tố cookies_ hoặc cookie_
    cookie_files = glob.glob("/data/files/cookies_*.txt") + glob.glob("/data/files/cookie_*.txt")
    cookie_files = list(set(cookie_files)) # Lọc trùng lặp nếu có
    
    if len(cookie_files) == 0:
        print("LỖI: Không tìm thấy file cookies nào. Vui lòng kiểm tra lại thư mục /data/files/")
        sys.exit(1)
        
    print(f"✅ Phát hiện {len(cookie_files)} kênh TikTok. Bắt đầu chiến dịch Quần Phát (Multi-Upload)...")
    
    worker_script = "/data/files/worker_upload.py"
    worker_code = """
import sys
import os
import playwright.sync_api
from tiktok_uploader.upload import upload_video

global_page = None

# HACK CLICK: Ép click mạnh và đợi lâu hơn
original_locator_click = playwright.sync_api.Locator.click
def force_locator_click(self, *args, **kwargs):
    kwargs['force'] = True 
    kwargs['timeout'] = 180000 
    return original_locator_click(self, *args, **kwargs)
playwright.sync_api.Locator.click = force_locator_click

# HACK WAIT_FOR: Ép thư viện phải đợi 3 phút (180,000ms) thay vì 60s
original_wait_for = playwright.sync_api.Locator.wait_for
def custom_wait_for(self, *args, **kwargs):
    kwargs['timeout'] = 180000 
    return original_wait_for(self, *args, **kwargs)
playwright.sync_api.Locator.wait_for = custom_wait_for

# HACK GOTO
original_goto = playwright.sync_api.Page.goto
def custom_goto(self, url, **kwargs):
    global global_page
    global_page = self
    kwargs['timeout'] = 180000
    response = original_goto(self, url, **kwargs)
    try:
        css_hack = "#react-joyride-portal, .react-joyride__overlay, .TUXModal-overlay, div[data-test-id='overlay'] { display: none !important; pointer-events: none !important; opacity: 0 !important; z-index: -9999 !important; }"
        self.add_style_tag(content=css_hack)
    except Exception:
        pass
    return response
playwright.sync_api.Page.goto = custom_goto

if __name__ == "__main__":
    cookie_path = sys.argv[3]
    account_name = os.path.basename(cookie_path).replace('.txt', '')
    try:
        # Bắt đầu gọi hàm upload
        upload_video(sys.argv[1], description=sys.argv[2], cookies=cookie_path, headless=True)
        print("WORKER_COMPLETED")
    except Exception as e:
        print(f"WORKER_ERROR: {e}")
    finally:
        # Chụp màn hình cuối cùng để theo dõi lỗi nếu có
        if global_page:
            try:
                global_page.wait_for_timeout(3000)
                shot_path = f"/data/files/debug_man_hinh_{account_name}.png"
                global_page.screenshot(path=shot_path)
                print(f"DA_CHUP_MAN_HINH: {shot_path}")
            except Exception:
                pass
"""
    
    with open(worker_script, 'w', encoding='utf-8') as f:
        f.write(worker_code)
    
    success_count = 0
    
    for index, cookie_path in enumerate(cookie_files):
        # 🌟 Trích xuất tên Kênh cho báo cáo chuyên nghiệp
        filename = os.path.basename(cookie_path)
        acc_name = filename.replace("cookies_", "").replace("cookie_", "").replace(".txt", "")
        
        print(f"\n[{index + 1}/{len(cookie_files)}] >>> Đang tiến hành đăng lên kênh: {acc_name.upper()} ({filename})")
        
        try:
            # Tăng tối đa mỗi kênh được phép mất 7 phút để xử lý upload
            result = subprocess.run(
                ['python3', worker_script, video_path, caption, cookie_path], 
                capture_output=True, text=True, timeout=420
            )
            
            full_log = result.stdout + "\n" + result.stderr
            
            if "WORKER_COMPLETED" in result.stdout and "Failed to upload" not in full_log:
                 print(f"✅ -> THÀNH CÔNG: Đã đăng video lên kênh {acc_name}!")
                 success_count += 1
            else:
                 print(f"❌ -> THẤT BẠI KÊNH {acc_name}:\n{full_log.strip()}")
                 
        except subprocess.TimeoutExpired:
             print(f"❌ -> THẤT BẠI: Kênh {acc_name} bị treo quá 7 phút!")
        except Exception as e:
            print(f"❌ -> THẤT BẠI HỆ THỐNG TẠI {acc_name}: {e}")
            
        # 🌟 BỘ CHỐNG SPAM: Nghỉ 15s giữa các lần up kênh để TikTok không chặn IP
        if index < len(cookie_files) - 1:
            print(f"⏳ Đang nghỉ 15 giây chống spam IP trước khi up kênh tiếp theo...")
            time.sleep(15)
    
    if success_count > 0:
        print(f"\nTIEN_TRINH_HOAN_TAT: Đã càn quét thành công {success_count}/{len(cookie_files)} kênh!")
    else:
        print("\nTẤT CẢ UPLOAD ĐỀU THẤT BẠI.")
        sys.exit(1)
