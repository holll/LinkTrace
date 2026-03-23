from tianyancha_client import BrowserManager, TianyanchaSearchService, ScreenshotService

def main():
    company_names = ["华为","小米","步步高"]

    with BrowserManager(use_saved_state=True) as browser:
        page = browser.new_page()

        search_service = TianyanchaSearchService(page)
        screenshot_service = ScreenshotService(page)

        for company_name in company_names:
            result = search_service.search_company_first(company_name)

            print("公司名:", result.company_name)
            print("链接:", result.company_url)

            output = screenshot_service.screenshot_page(result.company_url,result.company_name)
            print("截图:", output)

if __name__ == "__main__":
    main()
