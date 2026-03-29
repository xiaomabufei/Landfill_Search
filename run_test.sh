#!/bin/bash
# ============================================
#  Landfill Search — 测试搜索脚本
#  搜索 5 个新填埋场: Atella, Venosa, Lamezia Terme, Pianopoli, Celico
# ============================================

set -e
cd "$(dirname "$0")"

# ── 环境检测与构建 ─────────────────────────────

echo "🔍 检测 Python 环境..."

# 尝试激活 conda 环境
CONDA_OK=false
if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null
    if conda activate openai 2>/dev/null; then
        CONDA_OK=true
        echo "  ✅ conda 环境 'openai' 已激活"
    fi
fi

# 检查 python3 是否可用
if ! command -v python3 &>/dev/null; then
    echo "  ❌ 未找到 python3，请先安装 Python 3.8+"
    echo "     brew install python3"
    exit 1
fi

PY_VER=$(python3 --version 2>&1)
echo "  Python: $PY_VER"

# 检查并安装依赖
MISSING=()
for pkg in openpyxl playwright bs4 dotenv; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        MISSING+=("$pkg")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "  ⚠️  缺少依赖: ${MISSING[*]}"
    echo "  📦 自动安装依赖..."
    pip3 install -r requirements.txt -q
    if [ $? -ne 0 ]; then
        echo "  ❌ 依赖安装失败，请手动执行:"
        echo "     pip3 install -r requirements.txt"
        exit 1
    fi
    echo "  ✅ 依赖安装完成"
fi

# 检查 Playwright 浏览器
if ! python3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" 2>/dev/null; then
    echo "  ⚠️  Playwright 浏览器未安装，正在安装..."
    python3 -m playwright install chromium
    if [ $? -ne 0 ]; then
        echo "  ❌ Chromium 安装失败，请手动执行:"
        echo "     python3 -m playwright install chromium"
        exit 1
    fi
    echo "  ✅ Chromium 安装完成"
else
    echo "  ✅ Playwright + Chromium 就绪"
fi

echo ""

# ── 开始搜索 ─────────────────────────────────

echo "================================================"
echo "  Landfill Search — 测试搜索 5 个新填埋场"
echo "================================================"
echo ""
echo "  目标: Atella, Venosa, Lamezia Terme, Pianopoli, Celico"
echo "  模式: 有头（可见浏览器），单 Worker"
echo "  引擎: Google Search"
echo ""
echo "  ⚠️  如果弹出验证码，请在浏览器中手动点击通过"
echo ""
echo "================================================"
echo ""

# Phase 1: 自动搜索
echo "[Phase 1] 开始搜索..."
python3 -m src.search.scrape_runner data/raw/ITA.xlsx \
    --headed \
    --start 13 --end 18 \
    --engines google \
    --workers 1 \
    --batch-size 5

echo ""
echo "================================================"
echo ""

# Phase 2: 运行 Pipeline（检查 + 生成 HTML）
echo "[Phase 2] 运行 Pipeline..."
python3 main.py data/raw/ITA.xlsx

echo ""
echo "================================================"
echo "  ✅ 完成！查看结果:"
echo "  📄 搜索日志: logs/ITA_scrape_pipeline.md"
echo "  📄 Pipeline 日志: logs/ITA_pipeline.md"
echo "  ⚠️  错误日志: logs/ITA_errors.md"
echo "  📊 数据文件: output/ITA.json"
echo "  🌐 可视化: output/html/ITA.html"
echo "================================================"

# 自动打开 HTML
open output/html/ITA.html
