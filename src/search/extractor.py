"""信息提取器 — 从搜索结果中提取填埋场结构化数据。

通过关键词匹配和规则从 Google/Scholar/Maps 的原始搜索结果中
提取 landfill_type, gas_collection, start_year 等指标。
"""

import re
from typing import Dict, List, Optional, Tuple


def extract_landfill_type(results: List[Dict]) -> Tuple[Optional[str], Optional[Dict]]:
    """从搜索结果中提取填埋场类型。

    Returns:
        (type_value, ref_dict) 或 (None, None)
    """
    dump_keywords = ["dump", "open dump", "uncontrolled", "abusiva", "illegal",
                      "discarica abusiva", "scarico abusivo"]
    sanitary_keywords = ["sanitary landfill", "engineered landfill", "controlled landfill",
                          "non-hazardous waste", "rifiuti non pericolosi", "discarica controllata",
                          "discarica", "landfill", "rifiuti speciali", "piattaforma",
                          "smaltimento", "trattamento rifiuti"]

    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()

        for kw in sanitary_keywords:
            if kw in text:
                return "sanitary landfill", _make_ref(r)

        for kw in dump_keywords:
            if kw in text:
                return "dump", _make_ref(r)

    return None, None


def extract_gas_collection(results: List[Dict]) -> Tuple[Optional[str], Optional[Dict]]:
    """提取是否有填埋气收集。"""
    yes_keywords = ["biogas", "gas collection", "gas recovery", "captazione",
                     "recupero energetico", "biogas extraction", "landfill gas",
                     "methane capture", "flaring", "torcia", "biometano",
                     "energia elettrica", "cogenerazione", "produzione energetica"]
    no_keywords = ["no gas collection", "without gas", "senza captazione",
                    "no biogas", "nessuna captazione"]

    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()

        for kw in no_keywords:
            if kw in text:
                return "no", _make_ref(r)

        for kw in yes_keywords:
            if kw in text:
                return "yes", _make_ref(r)

    return None, None


def extract_gas_technology(results: List[Dict]) -> Tuple[Optional[str], Optional[Dict]]:
    """提取填埋气收集技术类型。"""
    tech_map = {
        "landfill gas collection with flaring": [
            "flaring", "flare", "torcia", "combustione", "gas flare"
        ],
        "landfill gas collection with electrification": [
            "electrification", "electricity", "power generation", "energia elettrica",
            "electric", "generation plant", "motore", "cogenerazione", "CHP"
        ],
        "landfill gas collection with purification": [
            "purification", "biomethane", "biometano", "upgrading",
            "gas purification", "methane purification", "raffinazione"
        ],
    }

    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
        for tech_name, keywords in tech_map.items():
            for kw in keywords:
                if kw in text:
                    return tech_name, _make_ref(r)

    return None, None


def extract_year(results: List[Dict], keywords: List[str]) -> Tuple[Optional[int], Optional[Dict]]:
    """从搜索结果中提取与关键词相关的年份。

    Args:
        keywords: 关键词列表，如 ["opened", "established", "start"]
    """
    year_pattern = re.compile(r'\b(19[5-9]\d|20[0-2]\d)\b')

    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()

        for kw in keywords:
            if kw in text:
                # 在关键词附近找年份
                kw_pos = text.find(kw)
                # 搜索关键词前后 100 字符内的年份
                context = text[max(0, kw_pos - 50):kw_pos + len(kw) + 100]
                years = year_pattern.findall(context)
                if years:
                    return int(years[0]), _make_ref(r)

    # fallback: 任何结果中的年份
    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
        years = year_pattern.findall(text)
        if years:
            return int(years[0]), _make_ref(r)

    return None, None


def extract_start_year(results: List[Dict]) -> Tuple[Optional[int], Optional[Dict]]:
    """提取建厂年份。"""
    keywords = ["opened", "established", "start", "inaugurat", "operational since",
                "anno apertura", "aperta nel", "attiva dal", "in operation since",
                "built in", "constructed", "dal ", "since ", "operativa dal",
                "in esercizio", "autorizzata nel", "realizzat"]
    return extract_year(results, keywords)


def extract_final_year(results: List[Dict]) -> Tuple[Optional[int], Optional[Dict]]:
    """提取关闭年份。"""
    keywords = ["closed", "closure", "shut down", "decommission", "exhausted",
                "chiusa", "chiusura", "esaurita", "dismessa", "cessata",
                "chiude", "revoca", "sequestro", "bonifica"]
    return extract_year(results, keywords)


def extract_gas_collection_rate(results: List[Dict]) -> Tuple[Optional[str], Optional[Dict]]:
    """提取填埋气收集率。"""
    rate_pattern = re.compile(r'(\d{1,3}(?:\.\d+)?)\s*%')

    rate_keywords = ["collection rate", "capture rate", "recovery rate",
                      "collection efficiency", "tasso di captazione", "efficienza"]

    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
        for kw in rate_keywords:
            if kw in text:
                kw_pos = text.find(kw)
                context = text[max(0, kw_pos - 30):kw_pos + len(kw) + 50]
                match = rate_pattern.search(context)
                if match:
                    return f"{match.group(1)}%", _make_ref(r)

    return None, None


def extract_general_info(results: List[Dict]) -> Dict:
    """从通用搜索结果中提取扩展指标。"""
    info = {}

    capacity_pattern = re.compile(r'([\d,.]+)\s*(?:m[³3]|cubic met)', re.IGNORECASE)
    area_pattern = re.compile(r'([\d,.]+)\s*(?:ha|hectare|ettari)', re.IGNORECASE)
    operator_keywords = ["managed by", "operated by", "gestita da", "gestore"]

    for r in results:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()

        # 容量
        if "waste_capacity_m3" not in info:
            match = capacity_pattern.search(text)
            if match:
                info["waste_capacity_m3"] = match.group(1).replace(",", "")

        # 面积
        if "area_hectares" not in info:
            match = area_pattern.search(text)
            if match:
                info["area_hectares"] = match.group(1).replace(",", "")

        # 运营方
        if "operator" not in info:
            for kw in operator_keywords:
                if kw in text:
                    kw_pos = text.find(kw)
                    after = text[kw_pos + len(kw):kw_pos + len(kw) + 50].strip()
                    # 取第一个逗号或句号前的内容
                    operator = re.split(r'[,.\n]', after)[0].strip()
                    if operator and len(operator) > 2:
                        info["operator"] = operator

    return info


def extract_all(search_results: Dict[str, List[Dict]],
                maps_result: Optional[Dict] = None,
                scholar_results: Optional[List[Dict]] = None) -> Dict:
    """从所有搜索结果中提取完整的结构化数据。

    Args:
        search_results: {"landfill_type": [...], "start_year": [...], ...}
        maps_result: Google Maps 搜索结果
        scholar_results: Google Scholar 搜索结果

    Returns:
        标准格式的填埋场数据字典
    """
    data = {}

    # 合并所有结果用于提取
    all_results = []
    for results in search_results.values():
        all_results.extend(results)
    if scholar_results:
        all_results.extend(scholar_results)

    # 提取核心指标
    lf_type, lf_type_ref = extract_landfill_type(
        search_results.get("landfill_type", []) + all_results
    )
    data["landfill_type"] = lf_type
    data["landfill_type_ref"] = lf_type_ref

    gc, gc_ref = extract_gas_collection(
        search_results.get("has_gas_collection", []) + all_results
    )
    data["has_gas_collection"] = gc
    data["has_gas_collection_ref"] = gc_ref

    tech, tech_ref = extract_gas_technology(
        search_results.get("gas_collection_technology", []) + all_results
    )
    data["gas_collection_technology"] = tech
    data["gas_collection_technology_ref"] = tech_ref

    rate, rate_ref = extract_gas_collection_rate(
        search_results.get("gas_collection_rate", []) + all_results
    )
    data["gas_collection_rate"] = rate
    data["gas_collection_rate_ref"] = rate_ref

    start, start_ref = extract_start_year(
        search_results.get("start_year", []) + all_results
    )
    data["start_year"] = start
    data["start_year_ref"] = start_ref

    final, final_ref = extract_final_year(
        search_results.get("final_year", []) + all_results
    )
    data["final_year"] = final
    data["final_year_ref"] = final_ref

    # gas_collection_start_year: 从 gas_collection 相关结果中提取
    gc_start_keywords = ["installed", "installation", "deployed", "since",
                          "installazione", "dal", "attivo dal"]
    gc_start, gc_start_ref = extract_year(
        search_results.get("has_gas_collection", []) +
        search_results.get("gas_collection_technology", []),
        gc_start_keywords
    )
    data["gas_collection_start_year"] = gc_start
    data["gas_collection_start_year_ref"] = gc_start_ref

    # 扩展指标
    general = extract_general_info(
        search_results.get("general_info", []) + all_results
    )
    data.update(general)

    # 补充 Maps 信息
    if maps_result:
        if not data.get("status") and maps_result.get("status"):
            data["status"] = maps_result["status"]
        if not data.get("operator") and maps_result.get("name"):
            # Maps 上的名字可能包含运营方信息
            pass

    return data


def _make_ref(result: Dict) -> Dict:
    """从搜索结果构造引用对象。"""
    url = result.get("url", "")
    title = result.get("title", "")

    # 推断来源类型
    ref_type = "other"
    if any(d in url for d in [".gov", ".gob", "regione.", "comune.", "provincia."]):
        ref_type = "government_report"
    elif any(d in url for d in ["scholar", "sciencedirect", "springer", "mdpi", "researchgate"]):
        ref_type = "academic_paper"
    elif any(d in url for d in ["news", "today", "press", "notizie", "cronaca", "giornale"]):
        ref_type = "news"
    elif any(d in url for d in ["wiki", "database", "catasto", "ispra"]):
        ref_type = "database"

    return {
        "source": title[:100] if title else None,
        "url": url if url else None,
        "type": ref_type,
    }
