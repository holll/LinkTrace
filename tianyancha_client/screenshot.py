class ScreenshotService:
    def __init__(self, page):
        self.page = page

    def screenshot_page(self, url, name):
        import os
        from PIL import Image
        page = self.page
        page.goto(url)
        page.wait_for_timeout(2000)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        os.makedirs("screenshots", exist_ok=True)

        full_path = f"screenshots/{name}_full.png"
        crop_path = f"screenshots/{name}.png"

        page.evaluate("""
            () => {

                // 只查 fixed 元素（性能更好）
                document.querySelectorAll('body *').forEach(el => {
                    const s = window.getComputedStyle(el);
                    if (s.position === 'fixed') {
                        el.remove();
                    }
                });

                document.querySelectorAll('[class*="risk-bar"]').forEach(el => el.remove());
                document.querySelectorAll('[class*="scroll-wrap"]').forEach(el => el.remove());

                document.querySelectorAll('[data-dim="baseInfo"]').forEach(el => {
                    (el.closest('.dim-section') || el).remove();
                });
                
                document.querySelectorAll('[data-dim="mapInfo"]').forEach(el => {
                    (el.closest('.dim-section') || el).remove();
                });

                document.getElementById('JS_Layout_Nav')?.remove();
                document.getElementById('JS_tag_nav')?.remove();

                document.querySelectorAll('[class*="bottom-bar-wrap"]').forEach(el => el.remove());

            }
        """)
        # 1) 先整页截图
        page.screenshot(
            path=full_path,
            full_page=True,
            animations="disabled"
        )

        # 2) 找主要人员区块 data-dim="staff"
        target = page.locator('[data-dim="staff"]').first

        if target.count() == 0:
            raise Exception('没找到 data-dim="staff" 的主要人员区块')

        # 可选：高亮调试
        target.evaluate("""
            el => el.style.outline = '3px solid red'
        """)
        page.wait_for_timeout(500)

        # 3) 计算该区块底部相对整页顶部的绝对 y 坐标
        crop_bottom = target.evaluate("""
            el => {
                const rect = el.getBoundingClientRect();
                return Math.ceil(rect.bottom + window.scrollY);
            }
        """)
        crop_bottom += 30
        if crop_bottom <= 0:
            raise Exception(f"计算得到的裁剪高度异常: {crop_bottom}")

        # 4) 用 Pillow 裁剪图片
        with Image.open(full_path) as img:
            width, height = img.size

            # 防止越界
            crop_bottom = min(crop_bottom, height)
            crop_bottom = max(1, crop_bottom)

            cropped = img.crop((0, 0, width, crop_bottom))
            cropped.save(crop_path)

        os.remove(full_path)
        return crop_path
