import argparse
from pathlib import Path

from config import HTML_DIR
from tianyancha_client import BrowserManager, TianyanchaSearchService, ScreenshotService
from tianyancha_client.relation_checker import (
    find_relations_in_project,
    load_persons_from_dir,
)
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


def check_person_relations(project_map, company_names):
    """基于已保存的详情页 HTML，检查同一项目内公司间的人员关联（法定代表人/股东/主要人员）。"""
    html_dir = Path(HTML_DIR)
    if not html_dir.is_dir():
        print("\n[关联检查] 未找到 html_pages/ 目录，跳过人员关联性检查")
        return

    persons_map = load_persons_from_dir(html_dir, company_names)
    print(f"\n[关联检查] 已提取 {len(persons_map)}/{len(company_names)} 家公司的法定代表人/股东/主要人员")

    missing = [n for n in company_names if n not in persons_map]
    if missing:
        print(f"[关联检查] 以下公司无详情页数据，未参与检查: {', '.join(missing)}")

    any_relation = False
    for project, suppliers in project_map.items():
        relations = find_relations_in_project(project, suppliers, persons_map)
        if not relations:
            continue
        any_relation = True
        print(f"\n[关联检查] 项目「{project}」检测到 {len(relations)} 组关联:")
        for r in relations:
            print(f"  - {r.company_a} <-> {r.company_b}")
            print(f"    判定依据: {r.summary()}")

    if not any_relation:
        print("[关联检查] 未检测到人员关联")


def main():
    args = parse_args()
    company_names, project_map = load_company_names(args.template)

    print("项目与供应商清单：")
    for project, suppliers in project_map.items():
        print(f"- {project}: {', '.join(suppliers)}")

    supplier_screenshot_map = {}
    failed_companies = []

    with BrowserManager(use_saved_state=True) as browser:
        page = browser.new_page()

        search_service = TianyanchaSearchService(page, browser)
        screenshot_service = ScreenshotService(page)
        HTML_DIR.mkdir(exist_ok=True)

        for company_name in company_names:
            try:
                result = search_service.search_company_first(company_name)
                print("公司名:", result.company_name)
                print("链接:", result.company_url)

                output = screenshot_service.screenshot_page(
                    result.company_url,
                    result.company_name,
                    html_save_path=str(HTML_DIR / f"{company_name}.html"),
                )
                supplier_screenshot_map[company_name] = output
                print("截图:", output)
            except Exception as e:
                print(f"[失败] {company_name}: {e}")
                failed_companies.append(company_name)

    if failed_companies:
        print(f"\n以下 {len(failed_companies)} 家供应商处理失败: {', '.join(failed_companies)}")

    check_person_relations(project_map, company_names)

    report_service = WordReportService()
    for project, suppliers in project_map.items():
        report_path = report_service.build_project_report(project, suppliers, supplier_screenshot_map)
        print("Word报告:", report_path)


if __name__ == "__main__":
    main()
