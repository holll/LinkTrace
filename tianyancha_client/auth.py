import time
from config import LOGIN_URL
from .selectors import Selectors
from .utils import is_login_url

def looks_like_logged_in(page):
    if is_login_url(page.url):
        return False
    return not page.locator("text=登录").first.is_visible(timeout=500)

def ensure_logged_in(page, browser):
    page.goto(LOGIN_URL)
    print("请登录...")
    start = time.time()
    while time.time() - start < 180:
        if not is_login_url(page.url):
            browser.save_storage_state()
            return
        page.wait_for_timeout(1000)
    raise RuntimeError("登录超时")
