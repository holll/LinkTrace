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
        links = self.page.locator(container_selector)
        if not links.count():
            links = self.page.locator(Selectors.COMPANY_LINK)

        # 天眼查搜索结果可能把相似公司排在前面（如"华为技术有限公司"搜出
        # "上海华为技术有限公司"排第一），优先选择与搜索词完全一致的条目
        link = self._find_exact_match(links, name)

        href = link.get_attribute("href")
        text = link.inner_text().strip()

        if not href:
            raise RuntimeError(f"未找到企业结果链接：{name}")
        if not text:
            raise RuntimeError(f"企业名称为空：{name}")

        return CompanySearchResult(text, href, 1)

    def _find_exact_match(self, links, name):
        """在搜索结果中查找名称完全一致的公司链接；无精确匹配时回退第一条。"""
        count = links.count()
        for i in range(count):
            if links.nth(i).inner_text().strip() == name.strip():
                return links.nth(i)
        return links.first
