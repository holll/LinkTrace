class Selectors:
    """天眼查页面选择器集中管理"""

    # 登录状态检测
    LOGIN_BUTTON = "text=登录"

    # 搜索结果
    SEARCH_RESULT_CONTAINER = ".search-result-single"
    COMPANY_LINK = 'a[href*="/company/"]'

    # 截图裁剪区域
    SECTION_STAFF = '[data-dim="staff"]'
    SECTION_BASE_INFO = '[data-dim="baseInfo"]'
    SECTION_MAP_INFO = '[data-dim="mapInfo"]'

    # 需要移除的干扰元素
    FIXED_ELEMENTS = "body *"
    RISK_BAR = '[class*="risk-bar"]'
    SCROLL_WRAP = '[class*="scroll-wrap"]'
    BOTTOM_BAR = '[class*="bottom-bar-wrap"]'
    LAYOUT_NAV = "#JS_Layout_Nav"
    TAG_NAV = "#JS_tag_nav"

    # 登录页判断
    LOGIN_URL_KEYWORD = "login"
