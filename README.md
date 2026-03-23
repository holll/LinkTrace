# LinkTrace（天眼查供应商截图工具）

该工具用于按供应商名称在天眼查搜索企业，并自动生成企业页面截图。

## 功能

- 自动搜索供应商并打开企业详情页。
- 自动裁剪页面到“主要人员（staff）”区块，避免整页超长图。
- 支持从模板批量导入“项目名称 + 供应商名称”列表。
- 首次登录后自动保存登录态，减少重复扫码登录。

## 环境准备

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## 模板格式

支持 `.xlsx` 或 `.csv` 文件，必须包含以下表头：

- `项目名称`
- `供应商名称`

示例：

| 项目名称 | 供应商名称 |
| --- | --- |
| 项目A | 华为 |
| 项目A | 小米 |
| 项目B | 步步高 |

> 空行会自动忽略；同一供应商会自动去重后再检索。

## 运行方式

### 1）不传模板（使用内置测试公司）

```bash
python app.py
```

### 2）传入模板（推荐）

```bash
python app.py --template ./suppliers.xlsx
```

运行后会在终端打印读取到的“项目 -> 供应商”映射，并在 `screenshots/` 目录输出截图文件。

## 常见问题

### 1）首次运行提示登录

程序会跳转登录页，登录成功后自动写入 `playwright_auth/tianyancha_state.json`。后续默认复用登录态。

### 2）模板报“表头缺失”

请确认第一行列名完全匹配：`项目名称`、`供应商名称`。

### 3）没有找到企业结果

可能是供应商名称不准确或页面结构变更，可在 `tianyancha_client/search.py` 中调整选择器。
