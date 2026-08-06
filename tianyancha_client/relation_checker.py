"""人员关联性检查：解析天眼查详情页 HTML，提取法定代表人/股东/主要人员，
判断同一项目内公司间是否存在人员关联。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# HTML 数据提取正则
_RE_LEGAL_BOX = re.compile(r'index_legal-name-box__[^"]*"[^>]*>(.*?)</td>', re.S)
_RE_HTML_TEXT = re.compile(r">([^<>]{2,40})<")
_RE_SHAREHOLDER_TITLE = re.compile(r'<h3[^>]*>(?:股东信息|主要股东)</h3>')
_RE_TABLE = re.compile(r"<table.*?</table>", re.S)
_RE_LEFT_COL_LINK = re.compile(
    r'<td[^>]*class="[^"]*left-col[^"]*".*?<a[^>]*link-click[^>]*>([^<]{1,40})</a>', re.S
)
_RE_STAFF_TITLE = re.compile(r"<h3[^>]*>主要人员</h3>")
_RE_LINK_CLICK = re.compile(r'<a[^>]*link-click[^>]*>([^<]{1,40})</a>')


@dataclass
class CompanyPersons:
    """从详情页提取的公司人员信息。"""

    company_name: str
    legal_representative: str = ""
    shareholders: List[str] = field(default_factory=list)
    staff: List[str] = field(default_factory=list)


@dataclass
class RelationResult:
    """两家公司之间的关联判定结果。"""

    company_a: str
    company_b: str
    matched_legal: str = ""
    matched_shareholders: List[str] = field(default_factory=list)
    matched_staff: List[str] = field(default_factory=list)

    @property
    def is_related(self) -> bool:
        return bool(self.matched_legal or self.matched_shareholders or self.matched_staff)

    def summary(self) -> str:
        parts = []
        if self.matched_legal:
            parts.append(f"法定代表人相同（{self.matched_legal}）")
        if self.matched_shareholders:
            parts.append(f"股东相同（{'、'.join(self.matched_shareholders)}）")
        if self.matched_staff:
            parts.append(f"主要人员相同（{'、'.join(self.matched_staff)}）")
        return "；".join(parts) if parts else "无"


_FIND_SECTION_JS = """
(titles) => {
    for (const h of document.querySelectorAll('.dimHeader_main-title-txt__GPoaZ')) {
        if (titles.includes(h.innerText.trim())) return h.closest('.dim-section');
    }
    return null;
}
"""

_LEGAL_REP_JS = """
() => {
    const td = document.querySelector('td[class*="legal-name-box"]');
    if (!td) return '';
    const a = td.querySelector('a[href*="/human/"]');
    return a ? a.innerText.trim() : '';
}
"""

_SCROLL_TO_SECTION_JS = """
(titles) => {
    for (const h of document.querySelectorAll('.dimHeader_main-title-txt__GPoaZ')) {
        if (titles.includes(h.innerText.trim())) {
            h.closest('.dim-section').scrollIntoView({block: 'center'});
            return true;
        }
    }
    return false;
}
"""

_COLLECT_ROWS_JS = """
({titles, selector}) => {
    const findSection = (titles) => {
        for (const h of document.querySelectorAll('.dimHeader_main-title-txt__GPoaZ')) {
            if (titles.includes(h.innerText.trim())) return h.closest('.dim-section');
        }
        return null;
    };
    const sec = findSection(titles);
    if (!sec) return [];
    const names = [];
    sec.querySelectorAll('table tbody tr').forEach(tr => {
        const a = tr.querySelector(selector);
        if (a && !names.includes(a.innerText.trim())) {
            names.push(a.innerText.trim());
        }
    });
    return names;
}
"""

_NEXT_PAGE_JS = """
(titles) => {
    const findSection = (titles) => {
        for (const h of document.querySelectorAll('.dimHeader_main-title-txt__GPoaZ')) {
            if (titles.includes(h.innerText.trim())) return h.closest('.dim-section');
        }
        return null;
    };
    const sec = findSection(titles);
    if (!sec) return false;
    const wrap = sec.querySelector('.pagination-wrap');
    if (!wrap) return false;
    const next = wrap.querySelector('.tic-laydate-next-m, [class*="next"]');
    const nums = [...wrap.querySelectorAll('.num')];
    const active = wrap.querySelector('.num.active');
    if (next && active && nums[nums.indexOf(active) + 1]) {
        next.click();
        return true;
    }
    return false;
}
"""

_WAIT_ROWS_JS = """
({titles, selector}) => {
    const findSection = (titles) => {
        for (const h of document.querySelectorAll('.dimHeader_main-title-txt__GPoaZ')) {
            if (titles.includes(h.innerText.trim())) return h.closest('.dim-section');
        }
        return null;
    };
    const sec = findSection(titles);
    if (!sec) return false;
    // 懒加载会先插入占位行，等待真正的数据行（目标选择器命中）出现
    return sec.querySelector(selector) !== null;
}
"""


def _collect_section_names(page, titles, name_selector, timeout_ms=8000):
    """滚动到区块触发懒加载，翻页收集全部名称（去重）。大公司表格分页时逐页提取。"""
    page.evaluate(_SCROLL_TO_SECTION_JS, titles)
    try:
        page.wait_for_function(
            _WAIT_ROWS_JS,
            arg={"titles": titles, "selector": name_selector},
            timeout=timeout_ms,
        )
    except Exception:
        pass

    names = []
    prev_first = None
    for _ in range(20):  # 最多翻 20 页
        rows = page.evaluate(_COLLECT_ROWS_JS, {"titles": titles, "selector": name_selector})
        if not rows:
            break
        if rows[0] == prev_first:  # 翻页后内容未变化，说明已到最后一页
            break
        names.extend(rows)
        prev_first = rows[0]
        if not page.evaluate(_NEXT_PAGE_JS, titles):
            break
        page.wait_for_timeout(1200)

    # 去重保序
    seen = set()
    return [n for n in names if not (n in seen or seen.add(n))]


def extract_persons_from_page(page) -> CompanyPersons:
    """直接从已加载的页面提取法定代表人/股东/主要人员（不依赖 HTML 文件）。

    表格数据为滚动懒加载且大公司分页展示，因此先滚动到区块触发加载，
    再逐页翻页收集全部行。
    """
    legal = page.evaluate(_LEGAL_REP_JS)
    shareholders = _collect_section_names(page, ["股东信息", "主要股东"], "td.left-col a")
    staff = _collect_section_names(page, ["主要人员"], 'td a[href*="/human/"]')

    return CompanyPersons(
        company_name="",
        legal_representative=legal,
        shareholders=shareholders,
        staff=staff,
    )


def _first_text(segment: str, exclude: str = "") -> str:
    for text in _RE_HTML_TEXT.findall(segment):
        text = text.strip()
        if text and text != exclude:
            return text
    return ""


def extract_company_persons(html_path: Path) -> CompanyPersons:
    """从单个天眼查详情页 HTML 提取法定代表人、股东、主要人员。"""
    html = html_path.read_text(encoding="utf-8")

    # 法定代表人：工商信息区块的法定代表人单元格
    legal = ""
    m = _RE_LEGAL_BOX.search(html)
    if m:
        legal = _first_text(m.group(1), exclude="法定代表人")

    # 股东：股东信息/主要股东区块表格的第一列
    shareholders: List[str] = []
    m = _RE_SHAREHOLDER_TITLE.search(html)
    if m:
        table = _RE_TABLE.search(html, m.end())
        if table:
            shareholders = [n.strip() for n in _RE_LEFT_COL_LINK.findall(table.group(0))]

    # 主要人员：主要人员区块表格的姓名列
    staff: List[str] = []
    m = _RE_STAFF_TITLE.search(html)
    if m:
        table = _RE_TABLE.search(html, m.end())
        if table:
            staff = [n.strip() for n in _RE_LINK_CLICK.findall(table.group(0))]

    return CompanyPersons(
        company_name=html_path.stem,
        legal_representative=legal,
        shareholders=shareholders,
        staff=staff,
    )


def find_relations_between(a: CompanyPersons, b: CompanyPersons) -> RelationResult:
    """比较两家公司，返回关联判定结果。"""
    result = RelationResult(company_a=a.company_name, company_b=b.company_name)

    if (
        a.legal_representative
        and a.legal_representative == b.legal_representative
    ):
        result.matched_legal = a.legal_representative

    set_a, set_b = set(a.shareholders), set(b.shareholders)
    result.matched_shareholders = sorted(set_a & set_b)

    set_a, set_b = set(a.staff), set(b.staff)
    result.matched_staff = sorted(set_a & set_b)

    return result


def find_relations_in_project(
    project_name: str,
    suppliers: List[str],
    persons_map: Dict[str, CompanyPersons],
) -> List[RelationResult]:
    """检查同一项目内任意两家供应商之间的人员关联（两两比较）。"""
    results: List[RelationResult] = []
    names = [n for n in suppliers if n in persons_map]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            result = find_relations_between(persons_map[names[i]], persons_map[names[j]])
            if result.is_related:
                result.company_a, result.company_b = names[i], names[j]
                results.append(result)
    return results


def load_persons_from_dir(html_dir: Path, company_names: List[str]) -> Dict[str, CompanyPersons]:
    """从 html 目录加载指定公司的提取结果（html 文件名形如 01_公司名.html）。"""
    persons_map: Dict[str, CompanyPersons] = {}
    by_name: Dict[str, Path] = {}
    for f in html_dir.glob("*.html"):
        name = f.stem.split("_", 1)[-1]
        by_name[name] = f

    for name in company_names:
        path = by_name.get(name)
        if path is None:
            continue
        persons = extract_company_persons(path)
        persons.company_name = name
        persons_map[name] = persons
    return persons_map
