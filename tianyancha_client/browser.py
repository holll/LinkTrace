from playwright.sync_api import sync_playwright

from config import BROWSER_PATH, HEADLESS, BROWSER_ARGS, VIEWPORT, USER_AGENT, STATE_FILE


class BrowserManager:
    def __init__(self, use_saved_state=True):
        self.use_saved_state = use_saved_state

    def __enter__(self):
        self.p = sync_playwright().start()
        if BROWSER_PATH is not None:
            self.browser = self.p.chromium.launch(
                executable_path=BROWSER_PATH,
                headless=HEADLESS,
                args=BROWSER_ARGS,
            )
        else:
            self.browser = self.p.chromium.launch(
                headless=HEADLESS,
                args=BROWSER_ARGS,
            )
        kwargs = {
            "viewport": VIEWPORT,
            "user_agent": USER_AGENT,
        }

        if self.use_saved_state and STATE_FILE.exists():
            kwargs["storage_state"] = str(STATE_FILE)

        self.context = self.browser.new_context(**kwargs)
        return self

    def new_page(self):
        return self.context.new_page()

    def save_storage_state(self):
        self.context.storage_state(path=str(STATE_FILE))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.context.close()
        self.browser.close()
        self.p.stop()
