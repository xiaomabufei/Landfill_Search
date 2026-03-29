"""Pipeline 和 Logger 测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import PipelineLogger, LOG_ROOT
from main import run_pipeline, derive_country_code


def test_country_code_derivation():
    """测试国家代码提取。"""
    assert derive_country_code("data/raw/ITA.xlsx") == "ITA"
    assert derive_country_code("some/path/deu.csv") == "DEU"
    assert derive_country_code("FRA.json") == "FRA"
    print("✅ test_country_code_derivation 通过")


def test_logger_creates_files():
    """测试 Logger 创建日志文件到 logs/ 目录。"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        log = PipelineLogger("TEST_LOG", log_dir=tmp)
        log.section("测试段落")
        log.info("普通信息")
        log.success("成功")
        log.fail("失败", reason="测试原因")
        log.warn("警告")
        log.close()

        # 主日志
        log_file = Path(tmp) / "TEST_LOG_pipeline.md"
        assert log_file.exists(), "主日志未创建"
        content = log_file.read_text(encoding="utf-8")
        assert "Pipeline Log — TEST_LOG" in content
        assert "`" in content  # 时间戳
        assert "✅ 成功" in content
        assert "🔴 失败" in content
        assert "color:red" in content

        # 错误日志
        err_file = Path(tmp) / "TEST_LOG_errors.md"
        assert err_file.exists(), "错误日志未创建"
        err_content = err_file.read_text(encoding="utf-8")
        assert "🔴" in err_content
        assert "🟡" in err_content

    print("✅ test_logger_creates_files 通过")


def test_logger_progress():
    """测试进度条。"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        log = PipelineLogger("PROG", log_dir=tmp)
        log.progress(1, 10, "test1")
        log.progress(5, 10, "test5")
        log.progress(10, 10, "test10")
        log.close()

        content = (Path(tmp) / "PROG_pipeline.md").read_text()
        assert "📊" in content
    print("✅ test_logger_progress 通过")


def test_logger_landfill_result():
    """测试折叠详情。"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        log = PipelineLogger("LF", log_dir=tmp)
        log.landfill_result("TestSite", 3, 5, {"type": "dump", "start": 2000})
        log.close()

        content = (Path(tmp) / "LF_pipeline.md").read_text()
        assert "<details>" in content
        assert "TestSite" in content
    print("✅ test_logger_landfill_result 通过")


def test_logger_no_error_file_when_clean():
    """无错误时不保留空错误日志。"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        log = PipelineLogger("CLEAN", log_dir=tmp)
        log.info("无错误")
        log.success("全部通过")
        log.close()

        err_file = Path(tmp) / "CLEAN_errors.md"
        assert not err_file.exists(), "无错误时不应保留错误日志"
    print("✅ test_logger_no_error_file_when_clean 通过")


def test_logs_saved_to_logs_dir():
    """日志默认保存到 logs/ 目录。"""
    log = PipelineLogger("DIRTEST")
    log.info("test")
    log.close()

    assert LOG_ROOT.exists(), "logs/ 目录不存在"
    log_file = LOG_ROOT / "DIRTEST_pipeline.md"
    assert log_file.exists(), f"日志未保存到 {log_file}"
    log_file.unlink()  # 清理
    print("✅ test_logs_saved_to_logs_dir 通过")


def test_pipeline_with_existing_json():
    """测试使用已有 JSON 运行 Pipeline。"""
    code = run_pipeline("data/raw/ITA.xlsx")
    assert code == 0

    assert Path("logs/ITA_pipeline.md").exists()
    assert Path("output/ITA.json").exists()
    assert Path("output/html/ITA.html").exists()
    print("✅ test_pipeline_with_existing_json 通过")


def test_pipeline_missing_input():
    """测试缺失输入文件。"""
    code = run_pipeline("data/raw/NONEXISTENT.xlsx")
    assert code == 1
    print("✅ test_pipeline_missing_input 通过")


def test_browser_detect():
    """测试浏览器检测。"""
    from src.search.browser_detect import detect_browsers, select_browsers
    browsers = detect_browsers()
    assert len(browsers) >= 1, "至少应检测到 1 个浏览器"

    selected = select_browsers(3)
    assert len(selected) >= 1
    assert len(selected) <= 3
    print(f"✅ test_browser_detect 通过 — 检测到 {len(browsers)} 个，选择 {len(selected)} 个")


if __name__ == "__main__":
    test_country_code_derivation()
    test_logger_creates_files()
    test_logger_progress()
    test_logger_landfill_result()
    test_logger_no_error_file_when_clean()
    test_logs_saved_to_logs_dir()
    test_pipeline_with_existing_json()
    test_pipeline_missing_input()
    test_browser_detect()
    print("\n🎉 Pipeline 测试全部通过!")
