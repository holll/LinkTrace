"""重截被验证码拦截的供应商截图；遇验证码等待用户手动验证后继续。"""
import random
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image

from tianyancha_client import BrowserManager, ScreenshotService

HTML_DIR = Path(__file__).resolve().parent / "html_pages"
SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots"


def main():
    targets = sys.argv[1:]
    if not targets:
        print("用法: python retry_screenshots.py 15 16 17 ...")
        return

    html_map = {}
    for f in sorted(HTML_DIR.glob("*.html")):
        if any(f.name.startswith(t) for t in targets):
            html = f.read_text(encoding="utf-8")
            m = re.search(r'href="(/company/\d+)"', html)
            if m:
                html_map[f.name] = "https://www.tianyancha.com" + m.group(1)

    ok, fail = [], []
    with BrowserManager(use_saved_state=True) as browser:
        page = browser.new_page()
        svc = ScreenshotService(page)

        for f in sorted(html_map):
            name = f[3:-5]
            url = html_map[f]
            time.sleep(random.uniform(3, 6))  # 降低访问频率，减少触发验证码
            try:
                cached = SCREENSHOT_DIR / f"{name}.png"
                if cached.exists():
                    cached.unlink()
                out = svc.screenshot_page(url, name)
                img = Image.open(out)
                ok.append((name, img.size))
                print(f"{name}: {img.size}")
            except Exception as e:
                fail.append((name, str(e)))
                print(f"[失败] {name}: {e}")

    print(f"\n成功 {len(ok)}，失败 {len(fail)}")
    for n, e in fail:
        print(f"  {n}: {e}")


if __name__ == "__main__":
    main()
