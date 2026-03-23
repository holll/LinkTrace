from urllib.parse import quote

from config import SEARCH_URL
from .auth import looks_like_logged_in, ensure_logged_in
from .models import CompanySearchResult


class TianyanchaSearchService:
    def __init__(self, page, browser_manager):
        self.page = page
        self.browser_manager = browser_manager

    def search_company_first(self, name):
        url = f"{SEARCH_URL}?key={quote(name)}"
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1200)

        if not looks_like_logged_in(self.page):
            ensure_logged_in(self.page, self.browser_manager)
            self.page.goto(url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(1200)

        link = self.page.locator('a[href*="/company/"]').first
        href = link.get_attribute("href")
        text = link.inner_text().strip()

        if not href:
            raise RuntimeError(f"未找到企业结果链接：{name}")

        return CompanySearchResult(text, href, 1)
