#!/usr/bin/env python3
"""Landfill Search — macOS GUI 应用

两种使用方式：
1. 输入填埋场名称 + 国家（可选）进行单个搜索
2. 选择文件（xlsx/csv/tsv/json）进行批量搜索
"""

import sys
import os
import json
import queue
import threading
import subprocess
import tempfile
from pathlib import Path
from multiprocessing import freeze_support

# 确保项目根目录在 path 中
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# ── 配置 ──

APP_TITLE = "Landfill Search"
APP_SIZE = "720x680"
OUTPUT_DIR = str(BASE_DIR / "output")
LOGS_DIR = str(BASE_DIR / "logs")


# ── GUI 应用 ──

class LandfillSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(APP_SIZE)
        self.root.resizable(True, True)

        self.msg_queue = queue.Queue()
        self.is_running = False
        self.result_html = None

        self._build_ui()
        self._poll_queue()
        self._check_environment()

    def _build_ui(self):
        # 主容器
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        # ── 标题 ──
        title_frame = ttk.Frame(main)
        title_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(title_frame, text="Landfill Search",
                  font=("Helvetica", 20, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="macOS only",
                  font=("Helvetica", 10), foreground="gray").pack(side=tk.RIGHT)

        # ── 模式选择 ──
        mode_frame = ttk.LabelFrame(main, text="搜索模式", padding=12)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        self.mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(mode_frame, text="单个搜索", variable=self.mode_var,
                        value="single", command=self._toggle_mode).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="批量搜索（文件）", variable=self.mode_var,
                        value="batch", command=self._toggle_mode).pack(side=tk.LEFT)

        # ── 单个搜索输入 ──
        self.single_frame = ttk.LabelFrame(main, text="单个填埋场搜索", padding=12)
        self.single_frame.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(self.single_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="填埋场名称:", width=12).pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.name_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)

        row2 = ttk.Frame(self.single_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="国家(可选):", width=12).pack(side=tk.LEFT)
        self.country_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.country_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── 批量搜索输入 ──
        self.batch_frame = ttk.LabelFrame(main, text="批量搜索（文件）", padding=12)

        file_row = ttk.Frame(self.batch_frame)
        file_row.pack(fill=tk.X, pady=2)
        self.file_var = tk.StringVar()
        ttk.Entry(file_row, textvariable=self.file_var, width=40, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(file_row, text="选择文件", command=self._browse_file).pack(side=tk.RIGHT)

        ttk.Label(self.batch_frame, text="支持格式: .xlsx  .csv  .tsv  .json",
                  foreground="gray").pack(anchor=tk.W, pady=(4, 0))

        # ── 操作按钮 ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=8)

        self.start_btn = ttk.Button(btn_frame, text="▶  开始搜索", command=self._start_search)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_btn = ttk.Button(btn_frame, text="📄 打开结果", command=self._open_result, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_log_btn = ttk.Button(btn_frame, text="📋 打开日志", command=self._open_logs, state=tk.DISABLED)
        self.open_log_btn.pack(side=tk.LEFT)

        # ── 进度 ──
        self.progress_var = tk.StringVar(value="就绪")
        ttk.Label(main, textvariable=self.progress_var, font=("Helvetica", 11)).pack(fill=tk.X, pady=(4, 2))

        self.progress_bar = ttk.Progressbar(main, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # ── 日志输出 ──
        log_frame = ttk.LabelFrame(main, text="运行日志", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=12, font=("Menlo", 11),
                                bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
                                wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 日志颜色标签
        self.log_text.tag_configure("success", foreground="#4ec9b0")
        self.log_text.tag_configure("error", foreground="#f44747", font=("Menlo", 11, "bold"))
        self.log_text.tag_configure("warn", foreground="#dcdcaa")
        self.log_text.tag_configure("info", foreground="#d4d4d4")
        self.log_text.tag_configure("dim", foreground="#808080")

        # ── 底部路径信息 ──
        self.path_var = tk.StringVar(value="")
        ttk.Label(main, textvariable=self.path_var, foreground="gray",
                  font=("Helvetica", 10)).pack(fill=tk.X, pady=(4, 0))

    def _toggle_mode(self):
        if self.mode_var.get() == "single":
            self.batch_frame.pack_forget()
            self.single_frame.pack(fill=tk.X, pady=(0, 8),
                                    after=self.single_frame.master.winfo_children()[1])
        else:
            self.single_frame.pack_forget()
            self.batch_frame.pack(fill=tk.X, pady=(0, 8),
                                   after=self.batch_frame.master.winfo_children()[1])

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="选择填埋场数据文件",
            filetypes=[
                ("所有支持格式", "*.xlsx *.xls *.csv *.tsv *.json"),
                ("Excel", "*.xlsx *.xls"),
                ("CSV", "*.csv"),
                ("TSV", "*.tsv"),
                ("JSON", "*.json"),
            ]
        )
        if path:
            self.file_var.set(path)

    def _check_environment(self):
        """检查运行环境。"""
        issues = []
        try:
            import openpyxl
        except ImportError:
            issues.append("缺少 openpyxl")
        try:
            import playwright
        except ImportError:
            issues.append("缺少 playwright")
        try:
            import bs4
        except ImportError:
            issues.append("缺少 beautifulsoup4")

        if issues:
            self._log(f"⚠️  环境问题: {', '.join(issues)}", "warn")
            self._log("请运行: pip install -r requirements.txt", "dim")
        else:
            self._log("✅ 环境检测通过", "success")

        # 检查浏览器
        chrome_exists = os.path.exists("/Applications/Google Chrome.app")
        pw_cache = Path.home() / "Library" / "Caches" / "ms-playwright"
        pw_exists = any(pw_cache.glob("chromium-*")) if pw_cache.exists() else False

        if chrome_exists:
            self._log("✅ Chrome 浏览器可用", "success")
        elif pw_exists:
            self._log("✅ Playwright Chromium 可用", "success")
        else:
            self._log("⚠️  未检测到 Chrome，首次搜索将自动安装 Chromium", "warn")

    def _start_search(self):
        if self.is_running:
            return

        if self.mode_var.get() == "single":
            name = self.name_var.get().strip()
            if not name:
                messagebox.showwarning("提示", "请输入填埋场名称")
                return
            self._run_in_thread(self._do_single_search, name, self.country_var.get().strip())
        else:
            path = self.file_var.get().strip()
            if not path or not os.path.exists(path):
                messagebox.showwarning("提示", "请选择有效的数据文件")
                return
            self._run_in_thread(self._do_batch_search, path)

    def _run_in_thread(self, func, *args):
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.progress_bar.start(10)
        self.progress_var.set("搜索中...")
        self._clear_log()

        thread = threading.Thread(target=func, args=args, daemon=True)
        thread.start()

    def _do_single_search(self, name, country):
        """单个填埋场搜索。"""
        try:
            country = country or "Unknown"
            code = name.upper().replace(" ", "_")[:10]

            # 创建临时 JSON 文件
            temp_data = [{
                "code": 1, "name": name,
                "lat": None, "lng": None,
                "country_code": code, "country": country,
            }]
            temp_path = os.path.join(tempfile.gettempdir(), f"landfill_{code}.json")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=4)

            self.msg_queue.put(("msg", f"搜索: {name} ({country})"))

            # 搜索
            from src.search.scrape_runner import run_scrape
            run_scrape(temp_path, output_dir=OUTPUT_DIR, headless=False,
                       batch_size=1, engines="google,scholar,maps", num_workers=1)

            # Pipeline
            from main import run_pipeline
            run_pipeline(temp_path, output_dir=OUTPUT_DIR)

            html_path = os.path.join(OUTPUT_DIR, "html", f"{code}.html")
            json_path = os.path.join(OUTPUT_DIR, f"{code}.json")

            if os.path.exists(html_path):
                self.result_html = html_path

            self.msg_queue.put(("done", {
                "html": html_path if os.path.exists(html_path) else None,
                "json": json_path if os.path.exists(json_path) else None,
            }))

        except Exception as e:
            self.msg_queue.put(("error", str(e)))

    def _do_batch_search(self, file_path):
        """批量文件搜索。"""
        try:
            code = Path(file_path).stem.upper()
            self.msg_queue.put(("msg", f"文件: {file_path}"))

            # 搜索
            from src.search.scrape_runner import run_scrape
            from src.logger import PipelineLogger

            def gui_callback(level, msg):
                self.msg_queue.put(("msg", msg))

            run_scrape(file_path, output_dir=OUTPUT_DIR, headless=False,
                       batch_size=10, engines="google,scholar,maps", num_workers=1)

            # Pipeline
            from main import run_pipeline
            run_pipeline(file_path, output_dir=OUTPUT_DIR)

            html_path = os.path.join(OUTPUT_DIR, "html", f"{code}.html")
            json_path = os.path.join(OUTPUT_DIR, f"{code}.json")

            if os.path.exists(html_path):
                self.result_html = html_path

            self.msg_queue.put(("done", {
                "html": html_path if os.path.exists(html_path) else None,
                "json": json_path if os.path.exists(json_path) else None,
            }))

        except Exception as e:
            self.msg_queue.put(("error", str(e)))

    def _poll_queue(self):
        """定期从队列取消息更新 GUI。"""
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()

                if msg_type == "msg":
                    # 根据内容决定颜色
                    tag = "info"
                    if "✅" in data:
                        tag = "success"
                    elif "🔴" in data or "❌" in data:
                        tag = "error"
                    elif "🟡" in data or "⚠️" in data:
                        tag = "warn"
                    elif data.startswith("  ") or "──" in data or "═" in data:
                        tag = "dim"
                    self._log(data, tag)

                elif msg_type == "done":
                    self._on_done(data)

                elif msg_type == "error":
                    self._log(f"❌ 错误: {data}", "error")
                    self._on_done(None)

        except queue.Empty:
            pass

        self.root.after(100, self._poll_queue)

    def _on_done(self, result):
        """搜索完成。"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.progress_bar.stop()

        if result and result.get("html"):
            self.progress_var.set("✅ 搜索完成")
            self.open_btn.config(state=tk.NORMAL)
            self.open_log_btn.config(state=tk.NORMAL)

            paths = []
            if result.get("json"):
                paths.append(f"JSON: {result['json']}")
            if result.get("html"):
                paths.append(f"HTML: {result['html']}")
            paths.append(f"日志: {LOGS_DIR}/")
            self.path_var.set("  |  ".join(paths))

            self._log("", "info")
            self._log(f"📊 结果: {result.get('json', '')}", "success")
            self._log(f"🌐 可视化: {result.get('html', '')}", "success")
            self._log(f"📋 日志目录: {LOGS_DIR}/", "dim")
        else:
            self.progress_var.set("搜索完成（部分失败）")
            self.open_log_btn.config(state=tk.NORMAL)
            self.path_var.set(f"日志目录: {LOGS_DIR}/")

    def _open_result(self):
        if self.result_html and os.path.exists(self.result_html):
            subprocess.run(["open", self.result_html])

    def _open_logs(self):
        subprocess.run(["open", LOGS_DIR])

    def _log(self, text, tag="info"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = LandfillSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    freeze_support()
    main()
