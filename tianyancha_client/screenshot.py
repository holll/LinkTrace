import os
import uuid

from PIL import Image


class ScreenshotService:
    def __init__(self, page):
        self.page = page

    def _get_section_bottom(self, selector):
        return self.page.evaluate(
            """
            (targetSelector) => {
                const el = document.querySelector(targetSelector);
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return Math.ceil(rect.bottom + window.scrollY + 30);
            }
            """,
            selector,
        )

    def screenshot_page(self, url, name):
        page = self.page
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        os.makedirs("screenshots", exist_ok=True)
        full_path = f"screenshots/{name}_{uuid.uuid4().hex}_full.png"
        output_path = f"screenshots/{name}.png"

        page.evaluate(
            """
            () => {
                document.querySelectorAll('body *').forEach(el => {
                    const s = window.getComputedStyle(el);
                    if (s.position === 'fixed') {
                        el.remove();
                    }
                });

                document.querySelectorAll('[class*="risk-bar"]').forEach(el => el.remove());
                document.querySelectorAll('[class*="scroll-wrap"]').forEach(el => el.remove());
                document.querySelectorAll('[class*="bottom-bar-wrap"]').forEach(el => el.remove());

                document.querySelectorAll('[data-dim="mapInfo"]').forEach(el => {
                    (el.closest('.dim-section') || el).remove();
                });

                document.getElementById('JS_Layout_Nav')?.remove();
                document.getElementById('JS_tag_nav')?.remove();
            }
            """
        )

        staff_bottom = self._get_section_bottom('[data-dim="staff"]')
        if staff_bottom is not None:
            page.evaluate(
                """
                () => {
                    document.querySelectorAll('[data-dim="baseInfo"]').forEach(el => {
                        (el.closest('.dim-section') || el).remove();
                    });
                }
                """
            )
            crop_bottom = staff_bottom
        else:
            base_info_bottom = self._get_section_bottom('[data-dim="baseInfo"]')
            if base_info_bottom is not None:
                crop_bottom = base_info_bottom
            else:
                crop_bottom = page.evaluate(
                    "() => Math.ceil(document.documentElement.scrollHeight)"
                )

        page.screenshot(path=full_path, full_page=True, animations="disabled")

        with Image.open(full_path) as img:
            width, height = img.size
            safe_bottom = max(1, min(crop_bottom, height))
            cropped = img.crop((0, 0, width, safe_bottom))
            cropped.save(output_path)

        if os.path.exists(full_path):
            os.remove(full_path)

        return output_path
