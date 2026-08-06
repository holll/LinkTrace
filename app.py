import argparse
from pathlib import Path

from config import HTML_DIR
from tianyancha_client import BrowserManager, TianyanchaSearchService, ScreenshotService
from tianyancha_client.relation_checker import (
    extract_persons_from_page,
    find_relations_in_project,
)
from tianyancha_client.utils import wait_manual_verify
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


def check_person_relations(project_map, persons_map):
    """检查同一项目内公司间的人员关联（法定代表人/股东/主要人员）。"""
    print(f"\n[关联检查] 已提取 {len(persons_map)} 家公司的法定代表人/股东/主要人员")

    missing = [n for n in set(n for suppliers in project_map.values() for n in suppliers)
               if n not in persons_map]
    if missing:
        print(f"[关联检查] 以下公司无数据，未参与检查: {', '.join(missing)}")

    project_relations = {}
    any_relation = False
    for project, suppliers in project_map.items():
        relations = find_relations_in_project(project, suppliers, persons_map)
        project_relations[project] = relations
        if not relations:
            continue
        any_relation = True
        print(f"\n[关联检查] 项目「{project}」检测到 {len(relations)} 组关联:")
        for r in relations:
            print(f"  - {r.company_a} <-> {r.company_b}")
            print(f"    判定依据: {r.summary()}")

    if not any_relation:
        print("[关联检查] 未检测到人员关联")
    return project_relations


def main():
    args = parse_args()
    company_names, project_map = load_company_names(args.template)

    print("项目与供应商清单：")
    for project, suppliers in project_map.items():
        print(f"- {project}: {', '.join(suppliers)}")

    supplier_screenshot_map = {}
    failed_companies = []
    persons_map = {}

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

                # 直接从页面提取人员信息存入内存（不依赖 HTML 文件）。
                # 截图缓存命中时页面可能不在目标详情页，需先导航过去。
                if not page.url.startswith(result.company_url):
                    page.goto(result.company_url, wait_until="domcontentloaded", timeout=60000)
                    wait_manual_verify(page)
                    for sel in ('[data-dim="staff"]', '[data-dim="baseInfo"]'):
                        try:
                            page.wait_for_selector(sel, timeout=5000)
                            break
                        except Exception:
                            continue
                persons = extract_persons_from_page(page)
                persons.company_name = company_name
                persons_map[company_name] = persons
            except Exception as e:
                print(f"[失败] {company_name}: {e}")
                failed_companies.append(company_name)

    if failed_companies:
        print(f"\n以下 {len(failed_companies)} 家供应商处理失败: {', '.join(failed_companies)}")

    project_relations = check_person_relations(project_map, persons_map)

    report_service = WordReportService()
    for project, suppliers in project_map.items():
        report_path = report_service.build_project_report(
            project,
            suppliers,
            supplier_screenshot_map,
            relations=project_relations.get(project),
        )
        print("Word报告:", report_path)


if __name__ == "__main__":
    main()
