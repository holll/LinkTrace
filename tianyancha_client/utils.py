import re
import time
from urllib.parse import urlparse

from .selectors import Selectors


def is_login_url(url: str) -> bool:
    return Selectors.LOGIN_URL_KEYWORD in (url or "").lower()


def is_verify_page(page) -> bool:
    """检测当前页面是否为人机验证页。"""
    url = (page.url or "").lower()
    if "verify" in url or "captcha" in url:
        return True
    try:
        return page.locator("text=身份验证").first.is_visible(timeout=800)
    except Exception:
        return False


def wait_manual_verify(page, timeout_minutes=10):
    """若当前为验证码页，等待用户在浏览器中手动完成验证后继续。"""
    if not is_verify_page(page):
        return
    print("\n[验证码] 检测到人机验证页面，请在浏览器窗口中手动完成验证（10 分钟内）...")
    start = time.time()
    while time.time() - start < timeout_minutes * 60:
        if not is_verify_page(page):
            print("[验证码] 验证已完成，继续处理...")
            page.wait_for_timeout(1500)
            return
        page.wait_for_timeout(2000)
    raise RuntimeError("等待手动验证超时，请重试")
