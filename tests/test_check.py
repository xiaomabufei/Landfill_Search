"""检查模块测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.check.validator import (
    check_format, check_logic, check_completeness,
    check_refs, validate_landfill, validate_country
)


def test_format_valid():
    """合规数据应无错误。"""
    lf = {"landfill_type": "sanitary landfill", "has_gas_collection": "yes",
          "gas_collection_technology": "landfill gas collection with flaring",
          "start_year": 2000, "final_year": 2020}
    issues = check_format(lf)
    assert len(issues) == 0, f"合规数据不应有错误: {issues}"
    print("✅ test_format_valid 通过")


def test_format_invalid_type():
    """非法 landfill_type 应报错。"""
    lf = {"landfill_type": "invalid_type"}
    issues = check_format(lf)
    assert len(issues) == 1
    assert issues[0]["level"] == "error"
    print("✅ test_format_invalid_type 通过")


def test_logic_no_gas_but_has_tech():
    """无 gas collection 但有技术应报错。"""
    lf = {"has_gas_collection": "no",
          "gas_collection_technology": "landfill gas collection with flaring"}
    issues = check_logic(lf)
    assert len(issues) == 1
    assert issues[0]["level"] == "error"
    print("✅ test_logic_no_gas_but_has_tech 通过")


def test_logic_start_after_final():
    """开始年份晚于关闭年份应报错。"""
    lf = {"start_year": 2020, "final_year": 2010}
    issues = check_logic(lf)
    assert len(issues) == 1
    print("✅ test_logic_start_after_final 通过")


def test_completeness():
    """缺失字段应标记警告。"""
    lf = {"landfill_type": "dump", "has_gas_collection": None,
          "gas_collection_technology": None, "gas_collection_rate": None,
          "start_year": None, "final_year": None, "gas_collection_start_year": None}
    issues = check_completeness(lf)
    assert len(issues) == 6  # 除 landfill_type 外 6 个缺失
    print("✅ test_completeness 通过")


def test_refs_missing():
    """有数据无来源应警告。"""
    lf = {"landfill_type": "dump", "landfill_type_ref": {"source": None, "url": None, "type": None}}
    issues = check_refs(lf)
    assert len(issues) == 1
    assert issues[0]["level"] == "warning"
    print("✅ test_refs_missing 通过")


def test_validate_country():
    """测试对 ITA.json 的完整检查。"""
    json_path = Path(__file__).parent.parent / "output" / "ITA.json"
    report = validate_country(str(json_path))
    assert report["total_landfills"] >= 10
    assert "errors" in report["summary"]
    assert "warnings" in report["summary"]
    print(f"✅ test_validate_country 通过 — 🔴{report['summary']['errors']} 🟡{report['summary']['warnings']} 🟢{report['summary']['passed']}")


if __name__ == "__main__":
    test_format_valid()
    test_format_invalid_type()
    test_logic_no_gas_but_has_tech()
    test_logic_start_after_final()
    test_completeness()
    test_refs_missing()
    test_validate_country()
    print("\n🎉 检查模块测试全部通过!")
