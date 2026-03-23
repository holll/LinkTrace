import argparse

from tianyancha_client import BrowserManager, TianyanchaSearchService, ScreenshotService
from tianyancha_client.report_writer import WordReportService
from tianyancha_client.template_loader import (
    group_suppliers_by_project,
    load_supplier_project_records,
)


def parse_args():
    parser = argparse.ArgumentParser(description="天眼查供应商信息截图工具")
    parser.add_argument(
        "--template",
        help="模板文件路径（.xlsx 或 .csv），需包含“项目名称”和“供应商名称”两列",
    )
    return parser.parse_args()


def load_company_names(template_path: str | None):
    if not template_path:
        default_names = ["华为", "小米", "步步高"]
        return default_names, {"默认项目": default_names}

    records = load_supplier_project_records(template_path)
    project_map = group_suppliers_by_project(records)

    seen = set()
    company_names = []
    for record in records:
        if record.supplier_name in seen:
            continue
        seen.add(record.supplier_name)
        company_names.append(record.supplier_name)

    return company_names, project_map


def main():
    args = parse_args()
    company_names, project_map = load_company_names(args.template)

    print("项目与供应商清单：")
    for project, suppliers in project_map.items():
        print(f"- {project}: {', '.join(suppliers)}")

    supplier_screenshot_map = {}

    with BrowserManager(use_saved_state=True) as browser:
        page = browser.new_page()

        search_service = TianyanchaSearchService(page, browser)
        screenshot_service = ScreenshotService(page)

        for company_name in company_names:
            result = search_service.search_company_first(company_name)
            print("公司名:", result.company_name)
            print("链接:", result.company_url)

            output = screenshot_service.screenshot_page(result.company_url, result.company_name)
            supplier_screenshot_map[company_name] = output
            print("截图:", output)

    report_service = WordReportService()
    for project, suppliers in project_map.items():
        report_path = report_service.build_project_report(project, suppliers, supplier_screenshot_map)
        print("Word报告:", report_path)


if __name__ == "__main__":
    main()
