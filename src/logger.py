"""Pipeline Logger — 同时输出到终端（ANSI 彩色）和 Markdown 日志文件。

日志文件保存到 logs/ 目录，搜索失败原因以 **加粗标红** 标记。
支持：进度条、ETA、时间戳、折叠详情、独立错误日志。
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List


# 日志根目录
LOG_ROOT = Path(__file__).parent.parent / "logs"


# ANSI 颜色码
class _C:
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD_RED = "\033[1;31m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_BLUE = "\033[1;34m"
    BOLD_CYAN = "\033[1;36m"


def _ts() -> str:
    """当前时间戳 HH:MM:SS。"""
    return datetime.now().strftime("%H:%M:%S")


def _format_duration(seconds: float) -> str:
    """格式化时长。"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.0f}m {seconds % 60:.0f}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"


class PipelineLogger:
    """Pipeline 日志记录器。

    日志文件保存到 logs/{run_name}_pipeline.md
    错误单独保存到 logs/{run_name}_errors.md
    """

    def __init__(self, run_name: str, log_dir: str = None, callback=None):
        """
        Args:
            run_name: 运行名称（如 "ITA", "ITA_scrape"）
            log_dir: 日志目录（默认 logs/）
            callback: 可选回调函数 callback(level, message)，用于 GUI 集成
        """
        self.run_name = run_name
        self._callback = callback
        self._log_dir = Path(log_dir) if log_dir else LOG_ROOT
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # 主日志
        self.log_path = self._log_dir / f"{run_name}_pipeline.md"
        self._file = open(self.log_path, "w", encoding="utf-8")

        # 错误日志
        self.error_log_path = self._log_dir / f"{run_name}_errors.md"
        self._error_file = open(self.error_log_path, "w", encoding="utf-8")

        self._step = 0
        self._errors = 0
        self._warnings = 0
        self._start_time = datetime.now()
        self._progress_times = []  # 用于计算 ETA
        self._worker_tag = ""  # 多进程时的 worker 标识

        # 写文件头
        ts = self._start_time.strftime("%Y-%m-%d %H:%M:%S")
        self._write_md(f"# Pipeline Log — {run_name}\n")
        self._write_md(f"> 开始时间: {ts}  ")
        self._write_md(f"> 日志文件: `{self.log_path}`  ")
        self._write_md(f"> 错误日志: `{self.error_log_path}`\n")
        self._write_md("---\n")
        self._write_md("## 目录\n")
        self._write_md("- [运行摘要](#运行摘要)\n")

        # 错误日志头
        self._write_err(f"# Error Log — {run_name}\n")
        self._write_err(f"> 开始时间: {ts}\n")
        self._write_err("---\n")

        # 终端头
        self._print(f"\n{_C.BOLD_BLUE}{'═' * 60}{_C.RESET}")
        self._print(f"{_C.BOLD}  Landfill Search Pipeline — {run_name}{_C.RESET}")
        self._print(f"{_C.DIM}  {ts}  |  日志: {self.log_path}{_C.RESET}")
        self._print(f"{_C.BOLD_BLUE}{'═' * 60}{_C.RESET}\n")

    def set_worker(self, tag: str):
        """设置当前 worker 标识（多进程用）。"""
        self._worker_tag = tag

    def section(self, title: str):
        """开始新的步骤段落。"""
        self._step += 1
        step_str = f"Step {self._step}"

        self._print(f"{_C.BOLD_BLUE}▸ [{step_str}] {title}{_C.RESET}")
        self._write_md(f"\n## {step_str}: {title}\n")

    def info(self, msg: str):
        """普通信息。"""
        tag = f"{self._worker_tag} " if self._worker_tag else ""
        self._print(f"  {_C.DIM}[{_ts()}]{_C.RESET} {tag}{msg}")
        self._write_md(f"- `{_ts()}` {tag}{msg}")

    def detail(self, msg: str):
        """次要细节信息。"""
        self._print(f"  {_C.DIM}[{_ts()}] {msg}{_C.RESET}")
        self._write_md(f"  - `{_ts()}` {msg}")

    def success(self, msg: str):
        """成功信息。"""
        tag = f"{self._worker_tag} " if self._worker_tag else ""
        self._print(f"  {_C.DIM}[{_ts()}]{_C.RESET} {_C.BOLD_GREEN}✅ {tag}{msg}{_C.RESET}")
        self._write_md(f"- `{_ts()}` ✅ {tag}{msg}")

    def fail(self, msg: str, reason: str = ""):
        """失败信息 — 终端加粗红色，Markdown 加粗标红。"""
        self._errors += 1
        tag = f"{self._worker_tag} " if self._worker_tag else ""
        full = f"{msg}" + (f" — {reason}" if reason else "")

        self._print(f"  {_C.DIM}[{_ts()}]{_C.RESET} {_C.BOLD_RED}🔴 {tag}{full}{_C.RESET}")
        self._write_md(f"- `{_ts()}` **<span style=\"color:red\">🔴 {tag}{full}</span>**")
        # 同时写入错误日志
        self._write_err(f"- `{_ts()}` 🔴 **{tag}{full}**")

    def warn(self, msg: str):
        """警告信息。"""
        self._warnings += 1
        tag = f"{self._worker_tag} " if self._worker_tag else ""
        self._print(f"  {_C.DIM}[{_ts()}]{_C.RESET} {_C.BOLD_YELLOW}🟡 {tag}{msg}{_C.RESET}")
        self._write_md(f"- `{_ts()}` 🟡 {tag}{msg}")
        self._write_err(f"- `{_ts()}` 🟡 {tag}{msg}")

    def progress(self, current: int, total: int, label: str = ""):
        """进度条 + ETA。"""
        now = time.time()
        self._progress_times.append(now)

        pct = current / total * 100 if total > 0 else 0
        bar_len = 30
        filled = int(bar_len * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)

        # 计算 ETA（用最近 10 个的平均速度）
        eta_str = ""
        if len(self._progress_times) >= 2:
            recent = self._progress_times[-min(10, len(self._progress_times)):]
            avg_time = (recent[-1] - recent[0]) / (len(recent) - 1)
            remaining = (total - current) * avg_time
            eta_str = f" | ETA: {_format_duration(remaining)}"
            avg_str = f" | {avg_time:.1f}s/个"
        else:
            avg_str = ""

        tag = f"{self._worker_tag} " if self._worker_tag else ""
        progress_line = f"{tag}[{bar}] {current}/{total} ({pct:.1f}%){eta_str}{avg_str}"

        if label:
            progress_line += f" | {label}"

        # 终端：覆盖同一行
        self._print(f"\r  {_C.BOLD_CYAN}[{_ts()}] {progress_line}{_C.RESET}")
        # Markdown：每 10% 或完成时记录
        if current == total or current % max(1, total // 10) == 0:
            self._write_md(f"- `{_ts()}` 📊 {progress_line}")

    def landfill_result(self, name: str, filled: int, total: int, details: dict = None):
        """记录单个填埋场搜索结果（Markdown 可折叠）。"""
        tag = f"{self._worker_tag} " if self._worker_tag else ""

        if filled == 0:
            icon = "🔴"
            color = _C.BOLD_RED
        elif filled < total:
            icon = "🟡"
            color = _C.BOLD_YELLOW
        else:
            icon = "🟢"
            color = _C.BOLD_GREEN

        self._print(f"  {_C.DIM}[{_ts()}]{_C.RESET} {color}{icon} {tag}{name}: {filled}/{total} 项{_C.RESET}")

        # Markdown 折叠详情
        if details:
            self._write_md(f"\n<details><summary><code>{_ts()}</code> {icon} {tag}{name}: {filled}/{total} 项</summary>\n")
            for field, value in details.items():
                if isinstance(value, dict) and "value" in value:
                    v = value["value"] or "—"
                    src = value.get("source", "")
                    self._write_md(f"- **{field}**: {v}" + (f" _(来源: {src})_" if src else ""))
                else:
                    v = value if value is not None else "—"
                    self._write_md(f"- **{field}**: {v}")
            self._write_md("\n</details>\n")
        else:
            self._write_md(f"- `{_ts()}` {icon} {tag}{name}: {filled}/{total} 项")

    def table(self, headers: list, rows: list):
        """输出表格。"""
        if not rows:
            return
        col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
        header_line = "  " + " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
        sep_line = "  " + "-+-".join("-" * w for w in col_widths)
        self._print(f"{_C.DIM}{header_line}{_C.RESET}")
        self._print(f"{_C.DIM}{sep_line}{_C.RESET}")
        for row in rows:
            self._print("  " + " | ".join(str(v).ljust(w) for v, w in zip(row, col_widths)))

        self._write_md("")
        self._write_md("| " + " | ".join(str(h) for h in headers) + " |")
        self._write_md("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            self._write_md("| " + " | ".join(str(v) for v in row) + " |")
        self._write_md("")

    def summary(self, stats: dict):
        """输出最终统计摘要。"""
        elapsed = (datetime.now() - self._start_time).total_seconds()

        self._print(f"\n{_C.BOLD_BLUE}{'═' * 60}{_C.RESET}")
        self._print(f"{_C.BOLD}  Pipeline 完成{_C.RESET}")
        self._print(f"{_C.BOLD_BLUE}{'═' * 60}{_C.RESET}")

        self._write_md("\n---\n")
        self._write_md("## 运行摘要\n")

        items = [
            ("耗时", _format_duration(elapsed)),
            ("错误数", str(self._errors)),
            ("警告数", str(self._warnings)),
        ]
        items.extend((k, str(v)) for k, v in stats.items())

        for label, value in items:
            if label == "错误数" and self._errors > 0:
                self._print(f"  {_C.BOLD_RED}{label}: {value}{_C.RESET}")
                self._write_md(f"- **<span style=\"color:red\">{label}: {value}</span>**")
            elif label == "警告数" and self._warnings > 0:
                self._print(f"  {_C.BOLD_YELLOW}{label}: {value}{_C.RESET}")
                self._write_md(f"- 🟡 {label}: {value}")
            else:
                self._print(f"  {label}: {value}")
                self._write_md(f"- {label}: {value}")

        # 文件指引
        self._print("")
        self._print(f"  {_C.DIM}📄 完整日志: {self.log_path}{_C.RESET}")
        if self._errors > 0 or self._warnings > 0:
            self._print(f"  {_C.DIM}⚠️  错误日志: {self.error_log_path}{_C.RESET}")

        self._write_md(f"\n> 📄 完整日志: `{self.log_path}`  ")
        if self._errors > 0 or self._warnings > 0:
            self._write_md(f"> ⚠️  错误日志: `{self.error_log_path}`")

    def close(self):
        """关闭日志文件。"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_md(f"\n---\n> 结束时间: {ts}")
        self._write_err(f"\n---\n> 结束时间: {ts}")
        self._file.close()
        self._error_file.close()

        # 如果没有错误/警告，删除空的错误日志
        if self._errors == 0 and self._warnings == 0:
            try:
                self.error_log_path.unlink()
            except Exception:
                pass

        self._print(f"\n{_C.DIM}  日志已保存: {self.log_path}{_C.RESET}\n")

    def _print(self, msg: str):
        print(msg, flush=True)
        if self._callback:
            # 去掉 ANSI 颜色码给 GUI
            import re
            clean = re.sub(r'\033\[[0-9;]*m', '', msg).strip()
            if clean:
                self._callback("msg", clean)

    def _write_md(self, line: str):
        self._file.write(line + "\n")
        self._file.flush()

    def _write_err(self, line: str):
        self._error_file.write(line + "\n")
        self._error_file.flush()
