from urllib.parse import quote

from config import SEARCH_URL
from .auth import looks_like_logged_in, ensure_logged_in
from .models import CompanySearchResult


class TianyanchaSearchService:
    def __init__(self, page):
        self.page = page

    def search_company_first(self, name):
        url = f"{SEARCH_URL}?key={quote(name)}"
        self.page.goto(url)
        self.page.wait_for_timeout(2000)

        if not looks_like_logged_in(self.page):
            ensure_logged_in(self.page)
            self.page.goto(url)

        link = self.page.locator('a[href*="/company/"]').first
        href = link.get_attribute("href")
        text = link.inner_text()

        return CompanySearchResult(text, href, 1)
