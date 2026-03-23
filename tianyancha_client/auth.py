import time

from config import LOGIN_URL
from .utils import is_login_url


def looks_like_logged_in(page):
    if is_login_url(page.url):
        return False
    return not page.locator("text=登录").first.is_visible(timeout=500)


def ensure_logged_in(page, browser_manager):
    page.goto(LOGIN_URL)
    print("请在 180 秒内完成登录...")
    start = time.time()

    while time.time() - start < 180:
        if not is_login_url(page.url):
            browser_manager.save_storage_state()
            return
        page.wait_for_timeout(1000)

    raise RuntimeError("登录超时，请重试")
