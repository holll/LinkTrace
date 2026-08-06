import time

from config import LOGIN_URL
from .selectors import Selectors
from .utils import is_login_url


def looks_like_logged_in(page):
    if is_login_url(page.url):
        return False
    try:
        page.locator(Selectors.LOGIN_BUTTON).first.wait_for(state="visible", timeout=500)
        return False
    except Exception:
        return True


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
