"""将搜索结果写入 JSON 文件。"""

from typing import List, Dict
import json
from datetime import datetime, timezone
from pathlib import Path


def build_landfill_json(landfill: dict, search_results: dict) -> dict:
    """将填埋场基础信息 + 搜索结果合并为 JSON 输出格式。"""

    def make_ref(ref_data):
        if ref_data is None:
            return {"source": None, "url": None, "type": None}
        return {
            "source": ref_data.get("source"),
            "url": ref_data.get("url"),
            "type": ref_data.get("type"),
        }

    return {
        "id": landfill["code"],
        "name": landfill["name"],
        "location": {
            "lat": landfill["lat"],
            "lng": landfill["lng"],
            "country": landfill["country"],
            "country_code": landfill["country_code"],
        },
        "landfill_type": search_results.get("landfill_type", {}).get("value"),
        "landfill_type_ref": make_ref(search_results.get("landfill_type", {}).get("ref")),
        "has_gas_collection": search_results.get("has_gas_collection", {}).get("value"),
        "has_gas_collection_ref": make_ref(search_results.get("has_gas_collection", {}).get("ref")),
        "gas_collection_technology": search_results.get("gas_collection_technology", {}).get("value"),
        "gas_collection_technology_ref": make_ref(search_results.get("gas_collection_technology", {}).get("ref")),
        "gas_collection_rate": search_results.get("gas_collection_rate", {}).get("value"),
        "gas_collection_rate_ref": make_ref(search_results.get("gas_collection_rate", {}).get("ref")),
        "start_year": search_results.get("start_year", {}).get("value"),
        "start_year_ref": make_ref(search_results.get("start_year", {}).get("ref")),
        "final_year": search_results.get("final_year", {}).get("value"),
        "final_year_ref": make_ref(search_results.get("final_year", {}).get("ref")),
        "gas_collection_start_year": search_results.get("gas_collection_start_year", {}).get("value"),
        "gas_collection_start_year_ref": make_ref(search_results.get("gas_collection_start_year", {}).get("ref")),
    }


def write_country_json(country: str, country_code: str, landfills_data: List[Dict], output_dir: str):
    """将一个国家的所有填埋场数据写入 JSON 文件。"""
    output = {
        "country": country,
        "country_code": country_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_version": "v1.0",
        "total_landfills": len(landfills_data),
        "landfills": landfills_data,
    }

    output_path = Path(output_dir) / f"{country_code}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"已写入: {output_path} ({len(landfills_data)} 个填埋场)")
    return str(output_path)
