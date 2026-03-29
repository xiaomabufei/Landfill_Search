"""搜索模块基础功能测试。"""

import sys
import json
import csv
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.search.reader import read_landfills, get_unfilled_landfills, get_batches, get_data_summary, ALL_INDICATORS
from src.search.query_builder import build_queries, build_batch_queries
from src.search.output_writer import build_landfill_json


def test_reader_xlsx():
    """测试 xlsx 读取。"""
    data_path = Path(__file__).parent.parent / "data" / "raw" / "ITA.xlsx"
    landfills = read_landfills(str(data_path))

    assert len(landfills) == 179, f"期望 179，实际 {len(landfills)}"
    assert landfills[0]["name"] == "Cupello"
    assert landfills[0]["country"] == "Italy"
    assert landfills[0]["lat"] is not None
    # 检查扩展字段存在（虽然为 None）
    assert "waste_capacity_m3" in landfills[0]
    assert "operator" in landfills[0]
    assert "area_hectares" in landfills[0]
    print("✅ test_reader_xlsx 通过")


def test_reader_csv():
    """测试 CSV 读取。"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Code1", "name", "lat", "lng", "GID_0", "Country", "landfill type"])
        writer.writerow([1, "TestSite", 42.0, 14.0, "ITA", "Italy", "dump"])
        writer.writerow([2, "TestSite2", 41.0, 13.0, "ITA", "Italy", ""])
        tmp_path = f.name

    landfills = read_landfills(tmp_path)
    assert len(landfills) == 2
    assert landfills[0]["name"] == "TestSite"
    assert landfills[0]["landfill_type"] == "dump"
    Path(tmp_path).unlink()
    print("✅ test_reader_csv 通过")


def test_reader_json():
    """测试 JSON 读取。"""
    test_data = [
        {"code": 1, "name": "JsonSite", "lat": 42.0, "lng": 14.0, "country_code": "ITA", "country": "Italy"},
        {"code": 2, "name": "JsonSite2", "lat": 41.0, "lng": 13.0, "country_code": "ITA", "country": "Italy"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(test_data, f)
        tmp_path = f.name

    landfills = read_landfills(tmp_path)
    assert len(landfills) == 2
    assert landfills[0]["name"] == "JsonSite"
    Path(tmp_path).unlink()
    print("✅ test_reader_json 通过")


def test_reader_tsv():
    """测试 TSV 读取。"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False, encoding="utf-8") as f:
        f.write("Code1\tname\tlat\tlng\tGID_0\tCountry\n")
        f.write("1\tTsvSite\t42.0\t14.0\tITA\tItaly\n")
        tmp_path = f.name

    landfills = read_landfills(tmp_path)
    assert len(landfills) == 1
    assert landfills[0]["name"] == "TsvSite"
    Path(tmp_path).unlink()
    print("✅ test_reader_tsv 通过")


def test_unfilled():
    """测试筛选未填写的填埋场。"""
    data_path = Path(__file__).parent.parent / "data" / "raw" / "ITA.xlsx"
    landfills = read_landfills(str(data_path))
    unfilled = get_unfilled_landfills(landfills)
    assert len(unfilled) == 179
    print("✅ test_unfilled 通过")


def test_batches():
    """测试批次分组。"""
    data_path = Path(__file__).parent.parent / "data" / "raw" / "ITA.xlsx"
    landfills = read_landfills(str(data_path))
    batches = get_batches(landfills, batch_size=10)
    assert len(batches) == 18
    assert len(batches[0]) == 10
    assert len(batches[-1]) == 9
    print("✅ test_batches 通过")


def test_data_summary():
    """测试数据概要统计。"""
    data_path = Path(__file__).parent.parent / "data" / "raw" / "ITA.xlsx"
    landfills = read_landfills(str(data_path))
    summary = get_data_summary(landfills)
    assert summary["total"] == 179
    assert summary["unfilled"] == 179
    assert "fields" in summary
    assert "landfill_type" in summary["fields"]
    assert "waste_capacity_m3" in summary["fields"]
    print("✅ test_data_summary 通过")


def test_extended_fields():
    """测试扩展指标字段存在。"""
    expected_extended = [
        "waste_capacity_m3", "annual_waste_intake_tons", "waste_types_accepted",
        "area_hectares", "operator", "depth_meters", "liner_type",
        "leachate_treatment", "status", "environmental_issues", "methane_emission_tons_year",
    ]
    for f in expected_extended:
        assert f in ALL_INDICATORS, f"扩展字段 {f} 不在 ALL_INDICATORS 中"
    print("✅ test_extended_fields 通过")


def test_query_builder():
    """测试搜索关键词构造。"""
    sample = {"name": "Malagrotta", "country": "Italy"}
    queries = build_queries(sample)
    assert "landfill_type" in queries
    assert "Malagrotta" in queries["landfill_type"][0]
    print("✅ test_query_builder 通过")


def test_output_writer():
    """测试 JSON 输出构造。"""
    landfill = {
        "code": 13945, "name": "Cupello", "lat": 42.05, "lng": 14.63,
        "country": "Italy", "country_code": "ITA",
    }
    search_results = {
        "landfill_type": {
            "value": "sanitary landfill",
            "ref": {"source": "ISPRA", "url": "https://example.com", "type": "government_report"},
        },
    }
    output = build_landfill_json(landfill, search_results)
    assert output["id"] == 13945
    assert output["landfill_type"] == "sanitary landfill"
    print("✅ test_output_writer 通过")


if __name__ == "__main__":
    test_reader_xlsx()
    test_reader_csv()
    test_reader_json()
    test_reader_tsv()
    test_unfilled()
    test_batches()
    test_data_summary()
    test_extended_fields()
    test_query_builder()
    test_output_writer()
    print("\n🎉 所有测试通过!")
