import os
import uuid

from PIL import Image

from config import SCREENSHOT_DIR
from .selectors import Selectors
from .utils import is_verify_page, wait_manual_verify

_CROP_TOP_OFFSET = 60  # 裁剪顶部偏移（像素），用于去掉页面顶部导航残留


class ScreenshotService:
    def __init__(self, page):
        self.page = page

    def _get_section_bottom(self, selector):
        """返回元素在文档中的底部坐标；元素不存在或不可见（高度为0）时返回 None。"""
        return self.page.evaluate(
            """
            (targetSelector) => {
                const el = document.querySelector(targetSelector);
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                if (rect.height === 0) return null;
                return Math.ceil(rect.bottom + window.scrollY + 30);
            }
            """,
            selector,
        )

    def _wait_for_page_ready(self, timeout_ms=30000):
        """页面就绪等待：等关键内容元素出现，再等区块内表格数据填充完成。"""
        page = self.page
        elapsed = 0
        step = 2000

        # 阶段一：等待任一关键内容元素出现
        candidates = [Selectors.SECTION_STAFF, Selectors.SECTION_BASE_INFO]
        hit = None
        for selector in candidates:
            remaining = timeout_ms - elapsed
            if remaining <= 0:
                break
            try:
                page.wait_for_selector(selector, timeout=min(step, remaining))
                hit = selector
                break
            except Exception:
                elapsed += step
                # 超时原因可能是人机验证页：等待用户手动完成验证后重新计时
                if is_verify_page(page):
                    wait_manual_verify(page)
                    elapsed = 0

        # 阶段一.5：容器出现不代表数据就绪（天眼查表格数据异步填充），
        # 等待页面内所有表格都不再显示"加载中"占位
        if hit is not None:
            remaining = timeout_ms - elapsed
            try:
                page.wait_for_function(
                    """() => {
                        const tbodies = document.querySelectorAll('table tbody');
                        for (const tb of tbodies) {
                            if (tb.innerText.includes('加载中')) return false;
                        }
                        return true;
                    }""",
                    timeout=max(0, min(5000, remaining)),
                )
                return
            except Exception:
                pass

        # 阶段二：兜底——给网络空闲一次短机会
        remaining = timeout_ms - elapsed
        if remaining > 0:
            try:
                page.wait_for_load_state("networkidle", timeout=min(5000, remaining))
            except Exception:
                pass

    def screenshot_page(self, url, name):
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        full_path = str(SCREENSHOT_DIR / f"{name}_{uuid.uuid4().hex}_full.png")
        output_path = str(SCREENSHOT_DIR / f"{name}.png")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path

        page = self.page

        # 导航 + 智能等待页面就绪
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        wait_manual_verify(page)
        self._wait_for_page_ready()

        # 移除干扰元素：先隐藏，等待渲染帧完成后再截图，避免空白闪烁
        page.evaluate(
            """
            () => {
                const toRemove = [];

                // 固定定位元素
                document.querySelectorAll('body *').forEach(el => {
                    const s = window.getComputedStyle(el);
                    if (s.position === 'fixed') {
                        toRemove.push(el);
                    }
                });

                // 风险栏 / 滚动包装 / 底部栏
                document.querySelectorAll('[class*="risk-bar"]').forEach(el => toRemove.push(el));
                document.querySelectorAll('[class*="scroll-wrap"]').forEach(el => toRemove.push(el));
                document.querySelectorAll('[class*="bottom-bar-wrap"]').forEach(el => toRemove.push(el));

                // 地图区块
                document.querySelectorAll('[data-dim="mapInfo"]').forEach(el => {
                    toRemove.push(el.closest('.dim-section') || el);
                });

                // 导航元素
                const nav = document.getElementById('JS_Layout_Nav');
                if (nav) toRemove.push(nav);
                const tagNav = document.getElementById('JS_tag_nav');
                if (tagNav) toRemove.push(tagNav);

                // 先全部隐藏（避免逐个 remove 引起的多次重排闪烁）
                toRemove.forEach(el => { el.style.display = 'none'; });
            }
            """
        )

        staff_bottom = self._get_section_bottom(Selectors.SECTION_STAFF)
        if staff_bottom is not None:
            page.evaluate(
                """
                () => {
                    document.querySelectorAll('[data-dim="baseInfo"]').forEach(el => {
                        const section = el.closest('.dim-section') || el;
                        section.style.display = 'none';
                    });
                }
                """
            )
            # 等待隐藏元素后的重排完成
            self._wait_render_frames()
            staff_bottom = self._get_section_bottom(Selectors.SECTION_STAFF)
            crop_bottom = staff_bottom
        else:
            self._wait_render_frames()
            base_info_bottom = self._get_section_bottom(Selectors.SECTION_BASE_INFO)
            crop_bottom = base_info_bottom

        if crop_bottom is None:
            crop_bottom = page.evaluate("() => Math.ceil(document.documentElement.scrollHeight)")

        # 等待浏览器完成渲染帧
        self._wait_render_frames()

        page.screenshot(path=full_path, full_page=True, animations="disabled")

        with Image.open(full_path) as img:
            width, height = img.size
            safe_bottom = max(1, min(crop_bottom, height))
            cropped = img.crop((0, _CROP_TOP_OFFSET, width, safe_bottom))
            cropped.save(output_path)

        if os.path.exists(full_path):
            os.remove(full_path)

        return output_path

    def _wait_render_frames(self):
        """等待浏览器完成两帧渲染，确保 DOM 变更已绘制。"""
        self.page.evaluate(
            """
            () => new Promise(resolve => {
                requestAnimationFrame(() => {
                    requestAnimationFrame(resolve);
                });
            })
            """
        )
