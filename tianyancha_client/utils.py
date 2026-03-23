import re
from urllib.parse import urlparse

def is_login_url(url: str) -> bool:
    return "login" in (url or "").lower()

def safe_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "home"
    path = re.sub(r"[^0-9a-zA-Z_\-]+", "_", path)
    return f"{parsed.netloc}_{path}.png"
