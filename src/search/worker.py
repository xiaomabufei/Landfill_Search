"""搜索 Worker — 单个浏览器实例的搜索执行单元。

每个 Worker 在独立进程中运行，拥有自己的浏览器实例。
通过 Queue 与主进程通信。
"""

import traceback
from typing import Dict, List, Optional

from .browser import BrowserSession, random_delay
from .browser_detect import BrowserSpec
from .google_search import search_landfill_all
from .google_scholar import search_landfill_scholar
from .google_maps import search_landfill_maps
from .extractor import extract_all


def make_null_ref():
    return {"source": None, "url": None, "type": None}


def build_output(raw: dict, extracted: dict) -> dict:
    """合并原始数据 + 提取结果为输出格式。"""
    def ref(key):
        r = extracted.get(key + "_ref")
        return r if r else make_null_ref()

    return {
        "id": raw.get("code"),
        "name": raw.get("name"),
        "location": {
            "lat": raw.get("lat"), "lng": raw.get("lng"),
            "region": "", "province": "",
        },
        "landfill_type": extracted.get("landfill_type"),
        "landfill_type_ref": ref("landfill_type"),
        "has_gas_collection": extracted.get("has_gas_collection"),
        "has_gas_collection_ref": ref("has_gas_collection"),
        "gas_collection_technology": extracted.get("gas_collection_technology"),
        "gas_collection_technology_ref": ref("gas_collection_technology"),
        "gas_collection_rate": extracted.get("gas_collection_rate"),
        "gas_collection_rate_ref": ref("gas_collection_rate"),
        "start_year": extracted.get("start_year"),
        "start_year_ref": ref("start_year"),
        "final_year": extracted.get("final_year"),
        "final_year_ref": ref("final_year"),
        "gas_collection_start_year": extracted.get("gas_collection_start_year"),
        "gas_collection_start_year_ref": ref("gas_collection_start_year"),
    }


def search_one_landfill(session: BrowserSession, lf: dict, country: str,
                         engine_list: List[str]) -> Dict:
    """搜索单个填埋场的全部指标。

    Returns:
        {"output": dict, "filled": int, "total": 5, "error": None}
        或 {"output": None, "filled": 0, "total": 5, "error": str}
    """
    name = lf.get("name", "Unknown")
    page = session.page
    check_fields = ["landfill_type", "has_gas_collection",
                     "gas_collection_technology", "start_year", "final_year"]

    try:
        # Google Search
        google_results = {}
        if "google" in engine_list:
            google_results = search_landfill_all(page, name, country)

        # Google Scholar
        scholar_results = []
        if "scholar" in engine_list:
            scholar_results = search_landfill_scholar(page, name, country)
            random_delay(3, 6)

        # Google Maps
        maps_result = None
        if "maps" in engine_list:
            maps_result = search_landfill_maps(
                page, name, country,
                lat=lf.get("lat"), lng=lf.get("lng"),
            )
            random_delay(3, 6)

        # 提取
        extracted = extract_all(google_results, maps_result, scholar_results)
        output_lf = build_output(lf, extracted)

        filled = sum(1 for k in check_fields if extracted.get(k) is not None)

        return {"output": output_lf, "filled": filled, "total": len(check_fields), "error": None}

    except Exception as e:
        return {"output": None, "filled": 0, "total": len(check_fields),
                "error": f"{type(e).__name__}: {e}"}


def worker_process(worker_id: int, spec: BrowserSpec, headless: bool,
                   task_queue, result_queue, engine_list: List[str],
                   country: str):
    """Worker 进程入口。

    从 task_queue 取任务，搜索后把结果放入 result_queue。
    发送 None 表示此 worker 结束。
    """
    tag = f"[W{worker_id}:{spec.name}]"

    try:
        session = BrowserSession(spec=spec, headless=headless, worker_id=worker_id)
        session.start()
        result_queue.put(("log", worker_id, "success", f"{tag} 浏览器启动成功"))
    except Exception as e:
        result_queue.put(("log", worker_id, "fail", f"{tag} 浏览器启动失败: {e}"))
        result_queue.put(("done", worker_id, None))
        return

    try:
        while True:
            task = task_queue.get()
            if task is None:  # 毒丸信号，退出
                break

            idx, lf = task
            name = lf.get("name", "Unknown")
            result_queue.put(("log", worker_id, "info", f"{tag} 搜索: {name}"))

            result = search_one_landfill(session, lf, country, engine_list)
            result_queue.put(("result", worker_id, idx, name, result))

    except KeyboardInterrupt:
        pass
    except Exception as e:
        result_queue.put(("log", worker_id, "fail", f"{tag} Worker 异常: {e}"))
    finally:
        session.close()
        result_queue.put(("done", worker_id, None))
