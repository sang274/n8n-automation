
import sys
import glob
import subprocess
import traceback

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)
    
    video_path = sys.argv[1]
    caption = sys.argv[2]
    
    cookie_files = glob.glob("/data/files/cookies*.txt")
    if len(cookie_files) == 0:
        print("LỖI: Không tìm thấy file cookies")
        sys.exit(1)
        
    print(f"Phát hiện {len(cookie_files)} kênh TikTok. Bắt đầu chiến dịch Quần Phát...")
    
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

# HACK WAIT_FOR: Ép thư viện phải đợi 3 phút (180,000ms) thay vì 60s để video kịp nén xong
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
    cookie_name = os.path.basename(cookie_path)
    try:
        # Bắt đầu gọi hàm upload
        upload_video(sys.argv[1], description=sys.argv[2], cookies=cookie_path, headless=True)
        print("WORKER_COMPLETED")
    except Exception as e:
        print(f"WORKER_ERROR: {e}")
    finally:
        # Chụp màn hình cuối cùng để theo dõi
        if global_page:
            try:
                global_page.wait_for_timeout(3000)
                shot_path = f"/data/files/debug_man_hinh_{cookie_name}.png"
                global_page.screenshot(path=shot_path)
                print(f"DA_CHUP_MAN_HINH: {shot_path}")
            except Exception:
                pass
"""
    
    with open(worker_script, 'w', encoding='utf-8') as f:
        f.write(worker_code)
    
    success_count = 0
    
    for cookie_path in cookie_files:
        print(f"\n>>> Đang khởi động tiến trình cho kênh: {cookie_path}")
        try:
            # Cho phép toàn bộ quá trình của mỗi tài khoản chạy tối đa 6 phút (360s)
            result = subprocess.run(
                ['python3', worker_script, video_path, caption, cookie_path], 
                capture_output=True, text=True, timeout=360
            )
            
            full_log = result.stdout + "\n" + result.stderr
            
            if "WORKER_COMPLETED" in result.stdout and "Failed to upload" not in full_log:
                 print(f"-> BÁO CÁO HOÀN THÀNH cho: {cookie_path}")
                 success_count += 1
            else:
                 print(f"-> THẤT BẠI KÊNH NÀY:\n{full_log}")
                 
        except subprocess.TimeoutExpired:
             print(f"-> THẤT BẠI: Kênh {cookie_path} bị treo quá 6 phút!")
        except Exception as e:
            print(f"-> THẤT BẠI HỆ THỐNG: {e}")
    
    if success_count > 0:
        print(f"\nTIEN_TRINH_HOAN_TAT: Đã càn quét thành công {success_count}/{len(cookie_files)} kênh!")
    else:
        print("\nTẤT CẢ UPLOAD ĐỀU THẤT BẠI.")
        sys.exit(1)
