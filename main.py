#!/usr/bin/env python3
"""Landfill Search Pipeline — 自动化运行脚本。

用法:
    python main.py data/raw/ITA.xlsx
    python main.py data/raw/ITA.xlsx --json output/ITA.json
    python main.py data/raw/ITA.xlsx --skip-html
    python main.py data/raw/ITA.xlsx -o results/
"""

import sys
import argparse
import json
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from src.logger import PipelineLogger
from src.search.reader import read_landfills, get_unfilled_landfills, get_data_summary, CORE_INDICATORS
from src.search.output_writer import write_country_json
from src.check.validator import validate_country, generate_check_report
from src.summary.html_generator import generate_html


def derive_country_code(file_path: str) -> str:
    """从文件名推导国家代码（如 ITA.xlsx → ITA）。"""
    return Path(file_path).stem.upper()


def run_pipeline(input_path: str, json_path: str = None, output_dir: str = None, skip_html: bool = False):
    """执行完整的 Pipeline。"""

    code = derive_country_code(input_path)
    if output_dir is None:
        output_dir = str(Path(__file__).parent / "output")
    html_dir = str(Path(output_dir) / "html")

    log = PipelineLogger(code)

    exit_code = 0

    # ── Step 1: 读取原始数据 ──────────────────────────────
    log.section("读取原始数据")
    try:
        log.info(f"文件: {input_path}")
        log.info(f"格式: {Path(input_path).suffix}")

        landfills = read_landfills(input_path)
        unfilled = get_unfilled_landfills(landfills)
        summary = get_data_summary(landfills)

        log.success(f"读取成功 — 共 {len(landfills)} 个填埋场")
        log.info(f"待搜索: {len(unfilled)} 个")
        log.info(f"国家代码: {code}")

        # 输出各字段完成情况
        fields_table = []
        for field, info in summary["fields"].items():
            if field in CORE_INDICATORS:
                status = "✅" if info["rate"] == 100 else f"{info['rate']}%"
                fields_table.append([field, f"{info['count']}/{summary['total']}", status])
        log.table(["指标", "已填/总数", "完成率"], fields_table)

    except FileNotFoundError:
        log.fail(f"文件不存在: {input_path}", reason="请检查文件路径是否正确")
        log.close()
        return 1
    except ValueError as e:
        log.fail(f"文件读取失败: {input_path}", reason=str(e))
        log.close()
        return 1
    except Exception as e:
        log.fail(f"读取异常: {type(e).__name__}", reason=str(e))
        log.close()
        return 1

    # ── Step 2: 加载搜索结果 ──────────────────────────────
    log.section("加载搜索结果")

    # 确定 JSON 路径
    if json_path is None:
        default_json = Path(output_dir) / f"{code}.json"
        if default_json.exists():
            json_path = str(default_json)

    if json_path and Path(json_path).exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            searched_count = len(json_data.get("landfills", []))
            log.success(f"加载搜索结果: {json_path}")
            log.info(f"已搜索填埋场: {searched_count} 个")

            # 统计搜索完成情况
            searched = json_data.get("landfills", [])
            if searched:
                filled_fields = 0
                total_fields = 0
                for lf in searched:
                    for field in CORE_INDICATORS:
                        total_fields += 1
                        if lf.get(field) is not None:
                            filled_fields += 1
                rate = round(filled_fields / total_fields * 100, 1) if total_fields > 0 else 0
                log.info(f"数据完整率: {rate}%")

                # 列出搜索失败的填埋场
                for lf in searched:
                    name = lf.get("name", "?")
                    missing = [f for f in CORE_INDICATORS if lf.get(f) is None]
                    if len(missing) == len(CORE_INDICATORS):
                        log.fail(f"{name}: 所有指标缺失", reason="搜索可能未覆盖此填埋场")
                    elif len(missing) > 0:
                        log.warn(f"{name}: 缺失 {len(missing)} 项 ({', '.join(missing[:3])}{'...' if len(missing) > 3 else ''})")
                    else:
                        log.success(f"{name}: 数据完整")

            remaining = len(landfills) - searched_count
            if remaining > 0:
                log.warn(f"尚有 {remaining} 个填埋场未搜索")

        except Exception as e:
            log.fail(f"JSON 加载失败: {json_path}", reason=str(e))
            json_path = None
    else:
        log.warn("未找到搜索结果 JSON 文件")
        log.info(f"期望路径: output/{code}.json")
        log.info("提示: 运行自动搜索生成数据:")
        log.info(f"  python -m src.search.scrape_runner {input_path} --headed")

    # ── Step 3: 数据检查 ──────────────────────────────────
    log.section("数据检查")

    if json_path and Path(json_path).exists():
        try:
            report = validate_country(json_path)
            s = report["summary"]

            log.info(f"检查 {report['total_landfills']} 个填埋场")

            # 按状态统计
            status_table = [
                ["🔴 错误", s["errors"]],
                ["🟡 警告", s["warnings"]],
                ["🟢 通过", s["passed"]],
                ["通过率", s["pass_rate"]],
            ]
            log.table(["状态", "数量"], status_table)

            # 输出具体错误
            for detail in report["details"]:
                errors = [i for i in detail["issues"] if i["level"] == "error"]
                for err in errors:
                    log.fail(
                        f"{detail['name']}: {err['field']}",
                        reason=err["msg"]
                    )

            # 生成检查报告
            report_path = str(Path(output_dir) / f"{code}_check_report.md")
            generate_check_report(report, report_path)
            log.success(f"检查报告: {report_path}")

        except Exception as e:
            log.fail("数据检查失败", reason=str(e))
            exit_code = 1
    else:
        log.warn("跳过 — 无搜索结果可检查")

    # ── Step 4: 生成 HTML 可视化 ──────────────────────────
    log.section("生成 HTML 可视化")

    if skip_html:
        log.info("已跳过（--skip-html）")
    elif json_path and Path(json_path).exists():
        try:
            html_path = str(Path(html_dir) / f"{code}.html")
            generate_html(json_path, html_path)
            log.success(f"HTML 已生成: {html_path}")
        except Exception as e:
            log.fail("HTML 生成失败", reason=str(e))
            exit_code = 1
    else:
        log.warn("跳过 — 无搜索结果可展示")

    # ── 输出摘要 ──────────────────────────────────────────
    stats = {
        "总填埋场": len(landfills),
        "已搜索": searched_count if json_path else 0,
        "未搜索": len(landfills) - (searched_count if json_path else 0),
    }
    if json_path:
        stats["数据完整率"] = f"{rate}%"
        stats["JSON"] = json_path
        if not skip_html:
            stats["HTML"] = str(Path(html_dir) / f"{code}.html")

    log.summary(stats)
    log.close()

    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="Landfill Search Pipeline — 自动化运行",
        usage="python main.py <input_file> [options]"
    )
    parser.add_argument("input", help="原始数据文件路径（支持 .xlsx/.csv/.tsv/.json）")
    parser.add_argument("-j", "--json", help="已有的搜索结果 JSON 文件路径", default=None)
    parser.add_argument("-o", "--output-dir", help="输出目录（默认 output/）", default=None)
    parser.add_argument("--skip-html", action="store_true", help="跳过 HTML 生成")
    parser.add_argument("--scrape", action="store_true", help="先执行自动搜索（通过 Chrome）再运行 Pipeline")
    parser.add_argument("--headed", action="store_true", help="搜索时显示浏览器窗口（需配合 --scrape）")
    parser.add_argument("--batch-size", type=int, default=10, help="搜索批次大小（默认 10）")
    parser.add_argument("--start", type=int, default=0, help="搜索起始索引")
    parser.add_argument("--end", type=int, default=None, help="搜索结束索引")

    args = parser.parse_args()

    # 如果启用了 --scrape，先执行自动搜索
    if args.scrape:
        from src.search.scrape_runner import run_scrape
        print("=" * 50)
        print("  Phase 1: 自动搜索")
        print("=" * 50)
        scrape_code = run_scrape(
            args.input, args.output_dir,
            headless=not args.headed,
            batch_size=args.batch_size,
            start=args.start, end=args.end,
        )
        if scrape_code != 0:
            print("搜索阶段出错，继续执行 Pipeline...")
        print("\n" + "=" * 50)
        print("  Phase 2: Pipeline 处理")
        print("=" * 50)

    code = run_pipeline(args.input, args.json, args.output_dir, args.skip_html)
    sys.exit(code)


if __name__ == "__main__":
    main()
