import os
from pathlib import Path


def find_system_chromium_browser():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


BROWSER_PATH = find_system_chromium_browser()
BASE_URL = "https://www.tianyancha.com"
LOGIN_URL = "https://www.tianyancha.com/login?type=1"
SEARCH_URL = "https://www.tianyancha.com/search"

PROJECT_ROOT = Path(__file__).resolve().parent
AUTH_DIR = PROJECT_ROOT / "playwright_auth"
AUTH_DIR.mkdir(exist_ok=True)

STATE_FILE = AUTH_DIR / "tianyancha_state.json"

SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

HEADLESS = False
VIEWPORT = {"width": 1440, "height": 900}

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--start-maximized",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
