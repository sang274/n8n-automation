
import sys
import playwright.sync_api
from tiktok_uploader.upload import upload_video

global_page = None

original_locator_click = playwright.sync_api.Locator.click
def force_locator_click(self, *args, **kwargs):
    kwargs['force'] = True 
    kwargs['timeout'] = 180000 
    return original_locator_click(self, *args, **kwargs)
playwright.sync_api.Locator.click = force_locator_click

original_wait_for = playwright.sync_api.Locator.wait_for
def custom_wait_for(self, *args, **kwargs):
    kwargs['timeout'] = 180000 
    return original_wait_for(self, *args, **kwargs)
playwright.sync_api.Locator.wait_for = custom_wait_for

original_goto = playwright.sync_api.Page.goto
def custom_goto(self, url, **kwargs):
    global global_page
    global_page = self
    kwargs['timeout'] = 180000
    response = original_goto(self, url, **kwargs)
    try:
        self.add_style_tag(content="#react-joyride-portal, .react-joyride__overlay, .TUXModal-overlay, div[data-test-id='overlay'] { display: none !important; opacity: 0 !important; z-index: -9999 !important; }")
    except: pass
    return response
playwright.sync_api.Page.goto = custom_goto

if __name__ == "__main__":
    try:
        upload_video(sys.argv[1], description=sys.argv[2], cookies=sys.argv[3], headless=True)
        print("TIEN_TRINH_HOAN_TAT")
    except Exception as e:
        print(f"LOI_UPLOAD: {e}")
