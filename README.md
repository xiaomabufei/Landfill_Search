# Landfill Search — 全球填埋场信息自动搜索与数据库构建

> **平台支持**: 目前仅在 **macOS** 上测试通过。Windows / Linux 未经验证。

通过 Playwright 驱动浏览器自动爬取 Google Search / Scholar / Maps，逐国采集全球填埋场的详细运营和环境数据，构建可溯源、可验证、可视化的填埋场数据库。

---

## 三种使用方式

| 方式 | 适合人群 | 说明 |
|------|---------|------|
| **[方式 A: macOS App](#方式-a-macos-app安装即用)** | 普通用户 | 双击打开，GUI 界面操作 |
| **[方式 B: Web UI](#方式-b-web-ui浏览器操作)** | 所有用户 | 浏览器打开，支持远程访问 |
| **[方式 C: 源码运行](#方式-c-源码运行)** | 开发者 | 命令行操作，可自定义参数 |

---

## 方式 A: macOS App（安装即用）

### 安装

```bash
# 克隆项目并打包
git clone https://github.com/xiaomabufei/Landfill_Search.git
cd Landfill_Search
./build_app.sh

# 安装到应用程序
cp -r "dist/Landfill Search.app" /Applications/
```

或直接双击 `dist/Landfill Search.app` 运行。

> 首次打开可能提示安全警告，右键 → "打开" 即可。

### 使用

1. **单个搜索**: 输入填埋场名称（如 `Malagrotta`），国家可选，点击"开始搜索"
2. **批量搜索**: 切换到"批量搜索"，选择数据文件（xlsx/csv/tsv/json），点击"开始搜索"
3. 搜索过程实时显示在日志窗口，进度、状态一目了然
4. 完成后点击"打开结果"查看 HTML 可视化，或"打开日志"查看详细记录

App 界面会显示：
- 搜索进度和状态
- 中间过程日志（成功/失败/警告）
- 结果文件路径（JSON / HTML / 日志）

---

## 方式 B: Web UI（浏览器操作）

```bash
pip install -r requirements.txt
python -m playwright install chromium
python web_app.py
```

浏览器打开 **http://localhost:5000**，即可使用：

1. **单个搜索**: 输入填埋场名称 + 国家（可选），点击搜索
2. **批量搜索**: 上传数据文件（xlsx/csv/tsv/json），自动处理
3. 实时查看搜索日志（成功/失败/警告高亮）
4. 搜索完成后直接点击查看 HTML 可视化、JSON 数据、检查报告

Web UI 特性：
- 深色日志面板，状态实时更新
- 结果文件直接在浏览器中打开/下载
- 支持局域网访问（`http://<你的IP>:5000`）

---

## 方式 C: 源码运行

### 1. 环境准备

```bash
git clone https://github.com/xiaomabufei/Landfill_Search.git
cd Landfill_Search
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. 一键测试

```bash
./run_test.sh
```

脚本会自动：检测环境 → 安装依赖 → 搜索 5 个填埋场 → 检查 → 生成 HTML → 打开结果。

> 如果弹出 Google 验证码，在浏览器中手动点击"I'm not a robot"即可。

### 3. GUI 模式

```bash
python gui_app.py
```

弹出图形界面，功能同 App 版本。

### 4. 命令行模式

```bash
# 自动搜索 + 检查 + 生成 HTML
python main.py data/raw/ITA.xlsx --scrape --headed

# 多浏览器并行搜索
python -m src.search.scrape_runner data/raw/ITA.xlsx --headed --workers 3

# 搜索指定范围（断点续搜，已搜过自动跳过）
python -m src.search.scrape_runner data/raw/ITA.xlsx --headed --start 0 --end 50

# 只用 Google（不搜 Scholar/Maps，更快）
python -m src.search.scrape_runner data/raw/ITA.xlsx --headed --engines google

# 只跑 Pipeline（已有搜索结果时）
python main.py data/raw/ITA.xlsx
```

### 5. 查看结果

| 文件 | 说明 |
|------|------|
| `output/html/ITA.html` | 地图 + 图表 + 表格可视化 |
| `output/ITA.json` | 结构化搜索结果（indent=4，含来源链接） |
| `output/ITA_check_report.md` | 数据检查报告 |
| `logs/ITA_pipeline.md` | Pipeline 运行日志 |
| `logs/ITA_errors.md` | 仅错误和警告 |

### 6. 运行测试

```bash
python tests/test_search.py      # 搜索模块（10 项）
python tests/test_check.py       # 检查模块（7 项）
python tests/test_summary.py     # 总结模块（3 项）
python tests/test_pipeline.py    # Pipeline + Logger（9 项）
```

---

## 项目架构

```
输入 ──→ 自动搜索 ──→ 信息提取 ──→ 数据检查 ──→ 输出
                Playwright         关键词规则     格式/逻辑
                Google/Scholar/Maps  英+意双语     完整性/来源

main.py        命令行入口（--scrape 触发搜索）
gui_app.py     GUI 入口（tkinter，可打包为 macOS .app）
web_app.py     Web UI 入口（Flask，http://localhost:5000）
run_test.sh    零配置测试脚本
build_app.sh   打包为 macOS .app
```

---

## 数据指标

### 核心指标（7 项，每项附来源链接）

| 指标 | 字段 | 取值 |
|------|------|------|
| 填埋场类型 | `landfill_type` | dump / sanitary landfill |
| 是否有填埋气收集 | `has_gas_collection` | yes / no |
| 收集技术类型 | `gas_collection_technology` | flaring / electrification / purification |
| 填埋气收集率 | `gas_collection_rate` | 数值% / null |
| 建厂年份 | `start_year` | 年份 |
| 关闭年份 | `final_year` | 年份 / null |
| 收集技术部署年份 | `gas_collection_start_year` | 年份 / null |

### 扩展指标（11 项）

容量、面积、运营方、防渗层、渗滤液处理、运营状态、环境问题、甲烷排放等。详见 [项目总览](docs/项目总览.md)。

---

## 当前进度

| 国家 | 填埋场总数 | 已搜索 | 完整率 |
|------|-----------|--------|--------|
| 意大利 | 179 | 13 | 54.9% |

---

## 日志系统

所有日志保存在 `logs/` 目录，详见 [logs/README.md](logs/README.md)。

- 每条带 `HH:MM:SS` 时间戳
- 失败原因 **加粗标红**
- 搜索结果可折叠展开
- 独立错误日志便于快速排查

---

## 目录结构

```
Landfill_Search/
├── main.py                          # 命令行入口
├── gui_app.py                       # GUI 入口（可打包为 macOS .app）
├── web_app.py                       # Web UI 入口（Flask，浏览器访问）
├── run_test.sh                      # 零配置测试脚本
├── build_app.sh                     # macOS .app 打包脚本
├── requirements.txt                 # Python 依赖
├── data/
│   └── raw/                         # 用户提供的原始数据文件
├── output/                          # 所有生成产物
│   ├── ITA.json                     # 搜索结果（indent=4）
│   ├── ITA_check_report.md          # 检查报告
│   ├── html/ITA.html                # 可视化页面
│   └── browser_state/               # 浏览器 cookies（自动管理）
├── logs/                            # 运行日志
│   ├── README.md                    # 日志说明
│   ├── ITA_pipeline.md
│   └── ITA_errors.md
├── docs/                            # 项目文档
│   ├── 项目总览.md
│   ├── 1_项目管理约束.md
│   ├── 2_搜索模块约束.md
│   ├── 3_检查模块约束.md
│   ├── 4_总结模块约束.md
│   └── 待办与需求.md
├── src/                             # 源代码
│   ├── logger.py                    # 日志系统（支持 GUI 回调）
│   ├── search/                      # 搜索模块（9 个文件）
│   ├── check/                       # 检查模块
│   └── summary/                     # 总结模块
└── tests/                           # 测试（29 项）
```

## 文档索引

| 文档 | 说明 |
|------|------|
| [项目总览](docs/项目总览.md) | 目标、架构、指标、工作流程、技术栈 |
| [1_项目管理约束](docs/1_项目管理约束.md) | 文档管理、Git 规范 |
| [2_搜索模块约束](docs/2_搜索模块约束.md) | 搜索引擎、提取规则、反爬策略 |
| [3_检查模块约束](docs/3_检查模块约束.md) | 检查维度、异常等级 |
| [4_总结模块约束](docs/4_总结模块约束.md) | JSON 规范、HTML 展示 |
| [待办与需求](docs/待办与需求.md) | 进度、已知问题、后续计划 |
| [日志说明](logs/README.md) | 日志格式和查看方式 |

---

## 面临的主要问题

1. **gas_collection_rate 极难获取** — 该指标在公开网页中极少出现
2. **小型填埋场信息稀缺** — 部分站点几乎无公开数据
3. **Google 反爬** — 频繁搜索触发验证码，需有头模式手动通过
4. **仅 macOS 测试** — Windows/Linux 未验证

详见 [待办与需求](docs/待办与需求.md)。
