#!/bin/bash
# ============================================
#  Landfill Search — 打包为 macOS .app
#  输出: dist/Landfill Search.app
# ============================================

set -e
cd "$(dirname "$0")"

echo "================================================"
echo "  Landfill Search — 打包 macOS App"
echo "================================================"
echo ""

# 激活 conda 环境
if command -v conda &>/dev/null; then
    source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null
    conda activate openai 2>/dev/null && echo "  ✅ conda 环境 'openai' 已激活"
fi

# 检查 PyInstaller
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "  📦 安装 PyInstaller..."
    pip3 install pyinstaller -q
fi

echo "  ✅ PyInstaller 就绪"

# 清理旧构建
rm -rf build dist *.spec

echo ""
echo "  🔨 开始构建..."
echo ""

# 构建 .app
python3 -m PyInstaller \
    --windowed \
    --onedir \
    --name "Landfill Search" \
    --add-data "src:src" \
    --add-data "data:data" \
    --add-data "logs:logs" \
    --add-data "output:output" \
    --collect-all playwright \
    --hidden-import openpyxl \
    --hidden-import bs4 \
    --hidden-import lxml \
    --hidden-import dotenv \
    --hidden-import src.search.browser \
    --hidden-import src.search.browser_detect \
    --hidden-import src.search.google_search \
    --hidden-import src.search.google_scholar \
    --hidden-import src.search.google_maps \
    --hidden-import src.search.extractor \
    --hidden-import src.search.scrape_runner \
    --hidden-import src.search.worker \
    --hidden-import src.search.reader \
    --hidden-import src.search.query_builder \
    --hidden-import src.search.output_writer \
    --hidden-import src.check.validator \
    --hidden-import src.summary.html_generator \
    --hidden-import src.logger \
    gui_app.py

echo ""
echo "================================================"

if [ -d "dist/Landfill Search.app" ]; then
    APP_SIZE=$(du -sh "dist/Landfill Search.app" | cut -f1)
    echo "  ✅ 构建成功!"
    echo "  📦 应用: dist/Landfill Search.app"
    echo "  📏 大小: $APP_SIZE"
    echo ""
    echo "  使用方式:"
    echo "    1. 双击 dist/Landfill Search.app 打开"
    echo "    2. 如提示安全警告，右键 → 打开"
    echo ""
    echo "  安装方式:"
    echo "    cp -r \"dist/Landfill Search.app\" /Applications/"
    echo "================================================"
else
    echo "  ❌ 构建失败，请查看上方错误信息"
    echo "================================================"
    exit 1
fi
