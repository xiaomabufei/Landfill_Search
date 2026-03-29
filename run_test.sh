#!/bin/bash
# ============================================
#  Landfill Search — 意大利填埋场全量搜索
#  自动搜索 ITA.xlsx 中所有剩余填埋场
# ============================================

set -e
cd "$(dirname "$0")"

# ── 环境检测与构建 ─────────────────────────────

echo "🔍 检测 Python 环境..."

# 尝试激活 conda 环境
if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null
    if conda activate openai 2>/dev/null; then
        echo "  ✅ conda 环境 'openai' 已激活"
    fi
fi

# 检查 python3
if ! command -v python3 &>/dev/null; then
    echo "  ❌ 未找到 python3，请先安装 Python 3.8+"
    echo "     brew install python3"
    exit 1
fi

echo "  Python: $(python3 --version 2>&1)"

# 检查并安装依赖
MISSING=()
for pkg in openpyxl playwright bs4 dotenv flask; do
    if ! python3 -c "import $pkg" 2>/dev/null; then
        MISSING+=("$pkg")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "  ⚠️  缺少依赖: ${MISSING[*]}"
    echo "  📦 自动安装..."
    pip3 install -r requirements.txt -q
    if [ $? -ne 0 ]; then
        echo "  ❌ 依赖安装失败，请手动: pip3 install -r requirements.txt"
        exit 1
    fi
    echo "  ✅ 依赖安装完成"
fi

# 检查 Playwright 浏览器
if ! python3 -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" 2>/dev/null; then
    echo "  ⚠️  Playwright 浏览器未安装，正在安装..."
    python3 -m playwright install chromium
    if [ $? -ne 0 ]; then
        echo "  ❌ Chromium 安装失败，请手动: python3 -m playwright install chromium"
        exit 1
    fi
    echo "  ✅ Chromium 安装完成"
else
    echo "  ✅ Playwright + Chromium 就绪"
fi

# 统计剩余数量
REMAINING=$(python3 -c "
import json
from src.search.reader import read_landfills
landfills = read_landfills('data/raw/ITA.xlsx')
try:
    with open('output/ITA.json') as f:
        existing = {lf['name'] for lf in json.load(f)['landfills']}
except: existing = set()
print(sum(1 for lf in landfills if lf['name'] not in existing))
")

TOTAL=$(python3 -c "from src.search.reader import read_landfills; print(len(read_landfills('data/raw/ITA.xlsx')))")
DONE=$((TOTAL - REMAINING))

echo ""
echo "================================================"
echo "  Landfill Search — 意大利全量搜索"
echo "================================================"
echo ""
echo "  总计: $TOTAL 个填埋场"
echo "  已完成: $DONE"
echo "  剩余: $REMAINING"
echo ""

if [ "$REMAINING" -eq 0 ]; then
    echo "  ✅ 所有填埋场已搜索完成！"
    echo ""
    echo "  直接运行 Pipeline..."
    python3 main.py data/raw/ITA.xlsx
    echo ""
    open output/html/ITA.html
    exit 0
fi

echo "  模式: 有头（可见浏览器），单 Worker"
echo "  引擎: Google Search"
echo "  批次: 每 10 个休息 30-60 秒"
echo "  断点续搜: 已搜过的自动跳过"
echo ""
echo "  ⚠️  如果弹出验证码，请在浏览器中手动点击通过"
echo "  ⚠️  按 Ctrl+C 可随时中断，进度自动保存，下次继续"
echo ""
echo "  预计耗时: 约 $((REMAINING * 70 / 60)) 分钟"
echo ""
echo "================================================"
echo ""

# Phase 1: 自动搜索（全量，断点续搜）
echo "[Phase 1] 开始搜索剩余 $REMAINING 个填埋场..."
echo ""

python3 -m src.search.scrape_runner data/raw/ITA.xlsx \
    --headed \
    --engines google \
    --workers 1 \
    --batch-size 10

echo ""
echo "================================================"
echo ""

# Phase 2: Pipeline（检查 + 生成 HTML）
echo "[Phase 2] 运行 Pipeline（检查 + 生成 HTML）..."
echo ""

python3 main.py data/raw/ITA.xlsx

echo ""
echo "================================================"
echo "  ✅ 完成！"
echo ""
echo "  📊 数据: output/ITA.json"
echo "  🌐 可视化: output/html/ITA.html"
echo "  📄 日志: logs/"
echo ""
echo "  查看错误: cat logs/ITA_errors.md"
echo "================================================"

# 自动打开 HTML
open output/html/ITA.html
