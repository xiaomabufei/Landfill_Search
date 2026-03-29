"""总结模块测试。"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.summary.html_generator import generate_html


def test_html_generation():
    """测试 HTML 文件生成。"""
    json_path = Path(__file__).parent.parent / "output" / "ITA.json"
    output_path = Path(__file__).parent.parent / "output" / "html" / "ITA_test.html"

    generate_html(str(json_path), str(output_path))

    assert output_path.exists(), "HTML 文件未生成"

    content = output_path.read_text(encoding="utf-8")
    assert "Italy" in content, "缺少国家名称"
    assert "Leaflet" in content or "leaflet" in content, "缺少 Leaflet 地图库"
    assert "Chart" in content or "chart" in content, "缺少 Chart.js 图表库"
    assert "Cupello" in content, "缺少填埋场数据"
    assert "Lanciano" in content, "缺少填埋场数据"
    assert "<table" in content, "缺少数据表格"

    # 清理测试文件
    output_path.unlink()
    print("✅ test_html_generation 通过")


def test_json_output_format():
    """测试 JSON 输出格式是否符合规范。"""
    json_path = Path(__file__).parent.parent / "output" / "ITA.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "country" in data
    assert "country_code" in data
    assert "generated_at" in data
    assert "data_version" in data
    assert "total_landfills" in data
    assert "landfills" in data
    assert len(data["landfills"]) == data["total_landfills"]

    # 检查每个填埋场的字段完整性
    required_fields = [
        "id", "name", "location", "landfill_type", "landfill_type_ref",
        "has_gas_collection", "has_gas_collection_ref",
        "gas_collection_technology", "gas_collection_technology_ref",
        "gas_collection_rate", "gas_collection_rate_ref",
        "start_year", "start_year_ref", "final_year", "final_year_ref",
        "gas_collection_start_year", "gas_collection_start_year_ref",
    ]
    for lf in data["landfills"]:
        for field in required_fields:
            assert field in lf, f"填埋场 {lf.get('name', '?')} 缺少字段 {field}"

    print("✅ test_json_output_format 通过")


def test_check_report_exists():
    """测试检查报告是否已生成。"""
    report_path = Path(__file__).parent.parent / "output" / "ITA_check_report.md"
    assert report_path.exists(), "检查报告未生成"

    content = report_path.read_text(encoding="utf-8")
    assert "检查报告" in content
    assert "Italy" in content
    print("✅ test_check_report_exists 通过")


if __name__ == "__main__":
    test_html_generation()
    test_json_output_format()
    test_check_report_exists()
    print("\n🎉 总结模块测试全部通过!")
