#!/usr/bin/env python3
"""批量搜索运行器 — 多浏览器并行搜索。

用法:
    python -m src.search.scrape_runner data/raw/ITA.xlsx --headed
    python -m src.search.scrape_runner data/raw/ITA.xlsx --headed --workers 2
    python -m src.search.scrape_runner data/raw/ITA.xlsx --start 0 --end 20
    python -m src.search.scrape_runner data/raw/ITA.xlsx --engines google
"""

import sys
import json
import argparse
import time
from multiprocessing import Process, Queue
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import PipelineLogger
from src.search.reader import read_landfills
from src.search.browser import BrowserSession, random_delay, batch_delay
from src.search.browser_detect import select_browsers, detect_browsers
from src.search.worker import worker_process, search_one_landfill, build_output
from src.search.extractor import extract_all


def load_existing(json_path: str) -> dict:
    """加载已有结果（断点续搜）。"""
    if Path(json_path).exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {lf["name"]: lf for lf in data.get("landfills", [])}
    return {}


def save_results(json_path: str, country: str, code: str, landfills: list):
    """保存结果到 JSON。"""
    output = {
        "country": country,
        "country_code": code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_version": "v0.3-parallel",
        "total_landfills": len(landfills),
        "landfills": landfills,
    }
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)


def run_scrape_single(target, country, code, json_path, existing,
                       headless, engine_list, batch_size, start, end, log):
    """单进程搜索（workers=1 或 fallback）。"""
    from src.search.browser_detect import BrowserSpec
    spec = select_browsers(1)[0]
    log.info(f"使用浏览器: {spec.name}")

    session = BrowserSession(spec=spec, headless=headless, worker_id=0)
    try:
        session.start()
        log.success(f"{spec.name} 启动成功")
    except Exception as e:
        log.fail("浏览器启动失败", reason=str(e))
        return 0, 0, 0

    all_results = list(existing.values())
    new_count = skip_count = fail_count = 0

    try:
        for i, lf in enumerate(target):
            name = lf.get("name", f"Unknown_{i}")
            idx = start + i + 1

            if name in existing:
                skip_count += 1
                log.detail(f"[{idx}/{end}] {name} — 跳过")
                continue

            log.progress(i + 1, len(target), name)
            result = search_one_landfill(session, lf, country, engine_list)

            if result["error"]:
                log.fail(f"{name}: 搜索异常", reason=result["error"])
                fail_count += 1
            elif result["filled"] == 0:
                log.landfill_result(name, 0, result["total"])
                fail_count += 1
            else:
                log.landfill_result(name, result["filled"], result["total"])

            if result["output"]:
                all_results.append(result["output"])
                new_count += 1

            save_results(json_path, country, code, all_results)

            if (i + 1) % batch_size == 0 and i + 1 < len(target):
                session.save_state()
                log.info(f"完成第 {(i + 1) // batch_size} 批，休息中...")
                batch_delay()

    except KeyboardInterrupt:
        log.warn("用户中断（Ctrl+C）")
    finally:
        save_results(json_path, country, code, all_results)
        session.close()

    return new_count, skip_count, fail_count


def run_scrape_parallel(target, country, code, json_path, existing,
                         headless, engine_list, batch_size, start, end,
                         num_workers, log):
    """多进程并行搜索。"""
    browsers = select_browsers(num_workers)
    actual_workers = len(browsers)
    log.info(f"并行 Workers: {actual_workers}")
    for i, b in enumerate(browsers):
        log.info(f"  W{i}: {b.name} ({b.engine})")

    # 准备任务队列
    task_queue = Queue()
    result_queue = Queue()

    tasks_added = 0
    for i, lf in enumerate(target):
        name = lf.get("name", "Unknown")
        if name not in existing:
            task_queue.put((start + i, lf))
            tasks_added += 1

    # 每个 worker 发一个毒丸
    for _ in range(actual_workers):
        task_queue.put(None)

    skip_count = len(target) - tasks_added
    if skip_count > 0:
        log.info(f"跳过已有结果: {skip_count} 个")
    log.info(f"待搜索: {tasks_added} 个")

    if tasks_added == 0:
        return 0, skip_count, 0

    # 启动 worker 进程
    workers = []
    for i, spec in enumerate(browsers):
        p = Process(
            target=worker_process,
            args=(i, spec, headless, task_queue, result_queue, engine_list, country),
            daemon=True,
        )
        # 错开启动，避免同时触发验证码
        if i > 0:
            time.sleep(3)
        p.start()
        workers.append(p)

    # 主进程：收集结果
    all_results = list(existing.values())
    new_count = 0
    fail_count = 0
    done_workers = 0
    completed = 0

    try:
        while done_workers < actual_workers:
            msg = result_queue.get(timeout=600)

            if msg[0] == "log":
                _, wid, level, text = msg
                if level == "success":
                    log.success(text)
                elif level == "fail":
                    log.fail(text)
                elif level == "warn":
                    log.warn(text)
                else:
                    log.info(text)

            elif msg[0] == "result":
                _, wid, idx, name, result = msg
                completed += 1

                if result["error"]:
                    log.fail(f"{name}: 搜索异常", reason=result["error"])
                    fail_count += 1
                elif result["filled"] == 0:
                    log.landfill_result(name, 0, result["total"])
                    fail_count += 1
                else:
                    log.landfill_result(name, result["filled"], result["total"])

                if result["output"]:
                    all_results.append(result["output"])
                    new_count += 1

                log.progress(completed, tasks_added)

                # 定期保存
                if completed % 5 == 0 or completed == tasks_added:
                    save_results(json_path, country, code, all_results)

            elif msg[0] == "done":
                done_workers += 1
                _, wid, _ = msg
                log.detail(f"Worker {wid} 已退出")

    except KeyboardInterrupt:
        log.warn("用户中断（Ctrl+C）")
    finally:
        save_results(json_path, country, code, all_results)
        for p in workers:
            p.terminate()
            p.join(timeout=5)

    return new_count, skip_count, fail_count


def run_scrape(input_path: str, output_dir: str = None, headless: bool = True,
               batch_size: int = 10, start: int = 0, end: int = None,
               engines: str = "google,scholar,maps", num_workers: int = 1):
    """执行批量搜索。"""
    code = Path(input_path).stem.upper()
    if output_dir is None:
        output_dir = str(Path(__file__).parent.parent.parent / "output")

    json_path = str(Path(output_dir) / f"{code}.json")
    engine_list = [e.strip() for e in engines.split(",")]
    log = PipelineLogger(f"{code}_scrape")

    # Step 1: 读取
    log.section("读取原始数据")
    try:
        landfills = read_landfills(input_path)
        log.success(f"共 {len(landfills)} 个填埋场")
    except Exception as e:
        log.fail("读取失败", reason=str(e))
        log.close()
        return 1

    country = landfills[0].get("country", "Unknown") if landfills else "Unknown"
    if end is None:
        end = len(landfills)
    target = landfills[start:end]
    log.info(f"搜索范围: [{start}:{end}]，共 {len(target)} 个")
    log.info(f"搜索引擎: {', '.join(engine_list)}")
    log.info(f"模式: {'无头' if headless else '有头'}")

    # Step 2: 检测浏览器
    log.section("检测可用浏览器")
    all_browsers = detect_browsers()
    log.info(f"检测到 {len(all_browsers)} 个浏览器:")
    for b in all_browsers:
        log.detail(f"{b.name} ({b.engine})")

    # Step 3: 断点续搜
    log.section("加载已有结果")
    existing = load_existing(json_path)
    log.info(f"已有 {len(existing)} 个结果")

    # Step 4: 搜索
    log.section(f"开始搜索（Workers: {num_workers}）")

    if num_workers <= 1:
        new_count, skip_count, fail_count = run_scrape_single(
            target, country, code, json_path, existing,
            headless, engine_list, batch_size, start, end, log)
    else:
        new_count, skip_count, fail_count = run_scrape_parallel(
            target, country, code, json_path, existing,
            headless, engine_list, batch_size, start, end, num_workers, log)

    log.success("搜索完成，结果已保存")

    # 摘要
    log.summary({
        "新搜索": new_count,
        "跳过(已有)": skip_count,
        "失败": fail_count,
        "输出": json_path,
    })
    log.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Landfill Search — 多浏览器并行搜索")
    parser.add_argument("input", help="原始数据文件路径")
    parser.add_argument("-o", "--output-dir", default=None)
    parser.add_argument("--headed", action="store_true", help="显示浏览器窗口")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--engines", default="google,scholar,maps",
                        help="搜索引擎（默认 google,scholar,maps）")
    parser.add_argument("--workers", type=int, default=1,
                        help="并行 Worker 数（默认 1，auto=自动检测浏览器数）")

    args = parser.parse_args()

    workers = args.workers
    if workers <= 0:  # --workers 0 或 auto
        workers = len(select_browsers(3))

    sys.exit(run_scrape(
        args.input, args.output_dir,
        headless=not args.headed,
        batch_size=args.batch_size,
        start=args.start, end=args.end,
        engines=args.engines,
        num_workers=workers,
    ))


if __name__ == "__main__":
    main()
