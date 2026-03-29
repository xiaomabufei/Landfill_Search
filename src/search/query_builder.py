"""根据填埋场信息构造搜索关键词。"""

from typing import Dict, List


# 每个指标对应的搜索关键词模板
QUERY_TEMPLATES = {
    "landfill_type": [
        "{name} landfill {country} dump OR sanitary",
        "{name} {country} landfill type waste disposal",
    ],
    "gas_collection": [
        "{name} landfill {country} gas collection technology",
        "{name} {country} landfill biogas recovery flaring",
    ],
    "gas_collection_rate": [
        "{name} landfill {country} gas collection rate efficiency",
    ],
    "start_year": [
        "{name} landfill {country} opening year established",
        "{name} {country} landfill construction start",
    ],
    "final_year": [
        "{name} landfill {country} closure closed year",
    ],
    "gas_collection_start_year": [
        "{name} landfill {country} gas collection system installation year",
    ],
}


def build_queries(landfill: dict) -> Dict[str, List[str]]:
    """为一个填埋场生成所有指标的搜索关键词。

    返回: {"landfill_type": ["query1", "query2"], ...}
    """
    name = landfill["name"]
    country = landfill["country"]

    queries = {}
    for indicator, templates in QUERY_TEMPLATES.items():
        queries[indicator] = [
            t.format(name=name, country=country) for t in templates
        ]
    return queries


def build_batch_queries(landfills: List[Dict]) -> List[Dict]:
    """为一批填埋场生成搜索关键词。

    返回: [{"landfill": {...}, "queries": {...}}, ...]
    """
    result = []
    for lf in landfills:
        result.append({
            "landfill": lf,
            "queries": build_queries(lf),
        })
    return result


if __name__ == "__main__":
    sample = {"name": "Malagrotta", "country": "Italy"}
    queries = build_queries(sample)
    for indicator, q_list in queries.items():
        print(f"\n{indicator}:")
        for q in q_list:
            print(f"  → {q}")
