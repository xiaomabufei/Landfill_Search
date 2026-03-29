"""检查模块：对搜索结果进行格式校验、逻辑校验和完整性检查。"""

from typing import List, Dict, Tuple
import json
from pathlib import Path


VALID_LANDFILL_TYPES = {"dump", "sanitary landfill"}
VALID_GAS_COLLECTION = {"yes", "no"}
VALID_GAS_TECHNOLOGIES = {
    "landfill gas collection with flaring",
    "landfill gas collection with electrification",
    "landfill gas collection with purification",
    "none",
}


def check_format(landfill: dict) -> List[Dict]:
    """格式校验：检查字段值是否合规。"""
    issues = []
    name = landfill.get("name", "unknown")

    # landfill_type
    val = landfill.get("landfill_type")
    if val is not None and val not in VALID_LANDFILL_TYPES:
        issues.append({"field": "landfill_type", "level": "error",
                        "msg": f"值 '{val}' 不合规，应为 dump 或 sanitary landfill"})

    # has_gas_collection
    val = landfill.get("has_gas_collection")
    if val is not None and val not in VALID_GAS_COLLECTION:
        issues.append({"field": "has_gas_collection", "level": "error",
                        "msg": f"值 '{val}' 不合规，应为 yes 或 no"})

    # gas_collection_technology
    val = landfill.get("gas_collection_technology")
    if val is not None and val not in VALID_GAS_TECHNOLOGIES:
        issues.append({"field": "gas_collection_technology", "level": "error",
                        "msg": f"值 '{val}' 不合规"})

    # start_year / final_year 应为合理年份
    for field in ["start_year", "final_year", "gas_collection_start_year"]:
        val = landfill.get(field)
        if val is not None and (not isinstance(val, (int, float)) or val < 1900 or val > 2030):
            issues.append({"field": field, "level": "error",
                            "msg": f"年份 '{val}' 不合理"})

    return issues


def check_logic(landfill: dict) -> List[Dict]:
    """逻辑校验：检查字段间的逻辑一致性。"""
    issues = []

    # 无 gas collection 时，相关字段应为 none/null
    has_gc = landfill.get("has_gas_collection")
    if has_gc == "no":
        if landfill.get("gas_collection_technology") not in (None, "none"):
            issues.append({"field": "gas_collection_technology", "level": "error",
                            "msg": "无 gas collection 但技术类型不为 none"})
        if landfill.get("gas_collection_rate") not in (None, "none"):
            issues.append({"field": "gas_collection_rate", "level": "error",
                            "msg": "无 gas collection 但收集率不为 none"})
        if landfill.get("gas_collection_start_year") is not None:
            issues.append({"field": "gas_collection_start_year", "level": "error",
                            "msg": "无 gas collection 但有部署年份"})

    # start_year 应早于 final_year
    start = landfill.get("start_year")
    final = landfill.get("final_year")
    if start is not None and final is not None:
        if isinstance(start, (int, float)) and isinstance(final, (int, float)):
            if start > final:
                issues.append({"field": "start_year/final_year", "level": "error",
                                "msg": f"开始年份({start})晚于关闭年份({final})"})

    # gas_collection_start_year 应晚于 start_year
    gc_start = landfill.get("gas_collection_start_year")
    if start is not None and gc_start is not None:
        if isinstance(start, (int, float)) and isinstance(gc_start, (int, float)):
            if gc_start < start:
                issues.append({"field": "gas_collection_start_year", "level": "error",
                                "msg": f"gas收集部署年份({gc_start})早于建厂年份({start})"})

    return issues


def check_completeness(landfill: dict) -> List[Dict]:
    """完整性检查：标记缺失的字段。"""
    issues = []
    indicator_fields = [
        "landfill_type", "has_gas_collection", "gas_collection_technology",
        "gas_collection_rate", "start_year", "final_year", "gas_collection_start_year"
    ]
    for field in indicator_fields:
        if landfill.get(field) is None:
            issues.append({"field": field, "level": "warning", "msg": "数据缺失"})

    return issues


def check_refs(landfill: dict) -> List[Dict]:
    """来源检查：有数据但无来源的情况。"""
    issues = []
    ref_pairs = [
        ("landfill_type", "landfill_type_ref"),
        ("has_gas_collection", "has_gas_collection_ref"),
        ("gas_collection_technology", "gas_collection_technology_ref"),
        ("gas_collection_rate", "gas_collection_rate_ref"),
        ("start_year", "start_year_ref"),
        ("final_year", "final_year_ref"),
        ("gas_collection_start_year", "gas_collection_start_year_ref"),
    ]
    for data_field, ref_field in ref_pairs:
        val = landfill.get(data_field)
        ref = landfill.get(ref_field, {})
        if val is not None and (ref is None or ref.get("url") is None):
            issues.append({"field": ref_field, "level": "warning",
                            "msg": f"'{data_field}' 有数据但无来源链接"})

    return issues


def validate_landfill(landfill: dict) -> Dict:
    """对单个填埋场执行全部检查。"""
    all_issues = []
    all_issues.extend(check_format(landfill))
    all_issues.extend(check_logic(landfill))
    all_issues.extend(check_completeness(landfill))
    all_issues.extend(check_refs(landfill))

    errors = [i for i in all_issues if i["level"] == "error"]
    warnings = [i for i in all_issues if i["level"] == "warning"]

    if errors:
        status = "error"
    elif warnings:
        status = "warning"
    else:
        status = "pass"

    return {
        "id": landfill.get("id"),
        "name": landfill.get("name"),
        "status": status,
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": all_issues,
    }


def validate_country(json_path: str) -> Dict:
    """对一个国家的 JSON 数据执行全部检查，生成检查报告。"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for lf in data["landfills"]:
        results.append(validate_landfill(lf))

    total = len(results)
    error_count = sum(1 for r in results if r["status"] == "error")
    warning_count = sum(1 for r in results if r["status"] == "warning")
    pass_count = sum(1 for r in results if r["status"] == "pass")

    return {
        "country": data["country"],
        "country_code": data["country_code"],
        "total_landfills": total,
        "summary": {
            "errors": error_count,
            "warnings": warning_count,
            "passed": pass_count,
            "pass_rate": f"{pass_count / total * 100:.1f}%" if total > 0 else "N/A",
        },
        "details": results,
    }


def generate_check_report(report: Dict, output_path: str):
    """生成 Markdown 格式的检查报告。"""
    lines = []
    lines.append(f"# 检查报告 — {report['country']} ({report['country_code']})\n")
    lines.append(f"共 {report['total_landfills']} 个填埋场\n")

    s = report["summary"]
    lines.append(f"| 状态 | 数量 |")
    lines.append(f"|------|------|")
    lines.append(f"| 🔴 错误 | {s['errors']} |")
    lines.append(f"| 🟡 警告 | {s['warnings']} |")
    lines.append(f"| 🟢 通过 | {s['passed']} |")
    lines.append(f"| 通过率 | {s['pass_rate']} |\n")

    for r in report["details"]:
        icon = {"error": "🔴", "warning": "🟡", "pass": "🟢"}[r["status"]]
        lines.append(f"## {icon} {r['name']} (ID: {r['id']})\n")
        if not r["issues"]:
            lines.append("无问题。\n")
        else:
            lines.append("| 字段 | 等级 | 说明 |")
            lines.append("|------|------|------|")
            for issue in r["issues"]:
                level_icon = "🔴" if issue["level"] == "error" else "🟡"
                lines.append(f"| {issue['field']} | {level_icon} | {issue['msg']} |")
            lines.append("")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"检查报告已生成: {output_path}")


if __name__ == "__main__":
    json_path = Path(__file__).parent.parent.parent / "output" / "ITA.json"
    report_path = Path(__file__).parent.parent.parent / "output" / "ITA_check_report.md"

    report = validate_country(str(json_path))
    generate_check_report(report, str(report_path))

    s = report["summary"]
    print(f"\n检查结果: 🔴{s['errors']} 🟡{s['warnings']} 🟢{s['passed']} (通过率 {s['pass_rate']})")
