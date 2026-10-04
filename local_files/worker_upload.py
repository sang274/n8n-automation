
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
