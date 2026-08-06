from urllib.parse import quote

from config import SEARCH_URL
from .auth import looks_like_logged_in, ensure_logged_in
from .models import CompanySearchResult
from .selectors import Selectors


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

        # 优先在搜索结果容器内查找，回退到全局查找
        container_selector = f"{Selectors.SEARCH_RESULT_CONTAINER} {Selectors.COMPANY_LINK}"
        link = self.page.locator(container_selector).first
        if not link.count():
            link = self.page.locator(Selectors.COMPANY_LINK).first

        href = link.get_attribute("href")
        text = link.inner_text().strip()

        if not href:
            raise RuntimeError(f"未找到企业结果链接：{name}")
        if not text:
            raise RuntimeError(f"企业名称为空：{name}")

        return CompanySearchResult(text, href, 1)
