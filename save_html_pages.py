"""从天眼查搜索清单中的公司，将详情页 HTML 保存到 html_pages/ 目录（调试用）。"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from tianyancha_client import BrowserManager, TianyanchaSearchService
from tianyancha_client.template_loader import load_supplier_project_records

HTML_DIR = Path(__file__).resolve().parent / "html_pages"
HTML_DIR.mkdir(exist_ok=True)


def safe_filename(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]+", "_", name).strip()


def main():
    template = sys.argv[1] if len(sys.argv) > 1 else "供应商关联性检测模板.xlsx"
    records = load_supplier_project_records(template)

    seen = set()
    companies = []
    for r in records:
        if r.supplier_name not in seen:
            seen.add(r.supplier_name)
            companies.append(r.supplier_name)

    print(f"共 {len(companies)} 家公司，开始处理...")
    saved, failed = [], []

    with BrowserManager(use_saved_state=True) as browser:
        page = browser.new_page()
        search_service = TianyanchaSearchService(page, browser)

        for i, name in enumerate(companies, 1):
            try:
                result = search_service.search_company_first(name)
                print(f"[{i}/{len(companies)}] {name} -> {result.company_url}")

                # 跳转到详情页并等待渲染
                page.goto(result.company_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)

                html = page.content()
                file_path = HTML_DIR / f"{i:02d}_{safe_filename(name)}.html"
                file_path.write_text(html, encoding="utf-8")
                saved.append(str(file_path))
                print(f"    保存: {file_path} ({len(html)} bytes)")
            except Exception as e:
                print(f"[失败] {name}: {e}")
                failed.append(name)

    print(f"\n完成：成功 {len(saved)}，失败 {len(failed)}")
    if failed:
        print(f"失败名单: {', '.join(failed)}")


if __name__ == "__main__":
    main()
