from playwright.sync_api import sync_playwright

from config import BROWSER_PATH, HEADLESS, BROWSER_ARGS, VIEWPORT, USER_AGENT, STATE_FILE


class BrowserManager:
    def __init__(self, use_saved_state=True):
        self.use_saved_state = use_saved_state

    def __enter__(self):
        self.p = sync_playwright().start()
        launch_kwargs = {"headless": HEADLESS, "args": BROWSER_ARGS}
        if BROWSER_PATH is not None:
            launch_kwargs["executable_path"] = BROWSER_PATH

        self.browser = self.p.chromium.launch(**launch_kwargs)

        context_kwargs = {
            "viewport": VIEWPORT,
            "user_agent": USER_AGENT,
        }
        if self.use_saved_state and STATE_FILE.exists():
            context_kwargs["storage_state"] = str(STATE_FILE)

        self.context = self.browser.new_context(**context_kwargs)
        return self

    def new_page(self):
        return self.context.new_page()

    def save_storage_state(self):
        self.context.storage_state(path=str(STATE_FILE))

    def __exit__(self, exc_type, exc_val, exc_tb):
        for attr in ("context", "browser", "p"):
            obj = getattr(self, attr, None)
            if obj is not None:
                try:
                    if attr == "p":
                        obj.stop()
                    else:
                        obj.close()
                except Exception:
                    pass
