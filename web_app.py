#!/usr/bin/env python3
"""Landfill Search — Web UI (Flask)

启动: python web_app.py
访问: http://localhost:5000
"""

import sys
import os
import json
import uuid
import threading
import tempfile
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template_string, request, jsonify, send_from_directory

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

app = Flask(__name__)

OUTPUT_DIR = str(BASE_DIR / "output")
LOGS_DIR = str(BASE_DIR / "logs")

# 任务状态存储
tasks = {}


# ── HTML 模板 ──

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landfill Search</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb; --primary-hover: #1d4ed8;
            --bg: #f8fafc; --card: #ffffff; --border: #e2e8f0;
            --text: #1e293b; --text2: #64748b; --text3: #94a3b8;
            --success: #10b981; --error: #ef4444; --warn: #f59e0b;
            --radius: 12px;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Inter',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }

        .header { background:var(--text); color:white; padding:20px 0; }
        .header-inner { max-width:900px; margin:0 auto; padding:0 24px; display:flex; justify-content:space-between; align-items:center; }
        .header h1 { font-size:22px; font-weight:700; }
        .header span { color:var(--text3); font-size:13px; }

        .container { max-width:900px; margin:32px auto; padding:0 24px; }

        .card { background:var(--card); border:1px solid var(--border); border-radius:var(--radius); padding:24px; margin-bottom:20px; }
        .card h2 { font-size:16px; font-weight:600; margin-bottom:16px; color:var(--text); }

        .tabs { display:flex; gap:0; margin-bottom:20px; }
        .tab { padding:10px 24px; border:1px solid var(--border); background:var(--bg); cursor:pointer; font-size:14px; font-weight:500; transition:all .2s; }
        .tab:first-child { border-radius:8px 0 0 8px; }
        .tab:last-child { border-radius:0 8px 8px 0; }
        .tab.active { background:var(--primary); color:white; border-color:var(--primary); }

        .form-row { display:flex; gap:12px; align-items:center; margin-bottom:12px; }
        .form-row label { font-size:13px; font-weight:500; color:var(--text2); min-width:90px; }
        .form-row input, .form-row select { flex:1; padding:10px 14px; border:1px solid var(--border); border-radius:8px; font-size:14px; outline:none; }
        .form-row input:focus { border-color:var(--primary); box-shadow:0 0 0 3px rgba(37,99,235,.1); }
        .form-row input[type="file"] { padding:8px; }

        .btn { padding:12px 28px; border:none; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; transition:all .2s; }
        .btn-primary { background:var(--primary); color:white; }
        .btn-primary:hover { background:var(--primary-hover); }
        .btn-primary:disabled { background:var(--text3); cursor:not-allowed; }
        .btn-outline { background:white; color:var(--primary); border:1px solid var(--primary); }
        .btn-outline:hover { background:rgba(37,99,235,.05); }

        .log-box { background:#1e1e2e; color:#cdd6f4; border-radius:8px; padding:16px; font-family:'Menlo',monospace;
                    font-size:12px; line-height:1.7; height:320px; overflow-y:auto; white-space:pre-wrap; }
        .log-box .success { color:#a6e3a1; }
        .log-box .error { color:#f38ba8; font-weight:bold; }
        .log-box .warn { color:#f9e2af; }
        .log-box .dim { color:#6c7086; }

        .status-bar { display:flex; gap:16px; align-items:center; margin-bottom:12px; }
        .status-dot { width:10px; height:10px; border-radius:50%; }
        .status-dot.idle { background:var(--text3); }
        .status-dot.running { background:var(--warn); animation:pulse 1s infinite; }
        .status-dot.done { background:var(--success); }
        .status-dot.error { background:var(--error); }
        @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }

        .results { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:16px; }
        .result-card { padding:14px; border:1px solid var(--border); border-radius:8px; }
        .result-card .label { font-size:11px; color:var(--text3); text-transform:uppercase; letter-spacing:.5px; }
        .result-card .value { font-size:14px; font-weight:600; margin-top:4px; }
        .result-card a { color:var(--primary); text-decoration:none; }
        .result-card a:hover { text-decoration:underline; }

        .hidden { display:none; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-inner">
            <h1>Landfill Search</h1>
            <span>macOS only · Web UI</span>
        </div>
    </div>

    <div class="container">
        <!-- 模式切换 -->
        <div class="tabs">
            <div class="tab active" onclick="switchTab('single')">单个搜索</div>
            <div class="tab" onclick="switchTab('batch')">批量搜索</div>
        </div>

        <!-- 单个搜索 -->
        <div class="card" id="single-panel">
            <h2>输入填埋场信息</h2>
            <div class="form-row">
                <label>填埋场名称</label>
                <input type="text" id="landfill-name" placeholder="如: Malagrotta">
            </div>
            <div class="form-row">
                <label>国家 (可选)</label>
                <input type="text" id="landfill-country" placeholder="如: Italy">
            </div>
            <button class="btn btn-primary" id="btn-single" onclick="startSingle()">开始搜索</button>
        </div>

        <!-- 批量搜索 -->
        <div class="card hidden" id="batch-panel">
            <h2>选择数据文件</h2>
            <div class="form-row">
                <label>数据文件</label>
                <input type="file" id="data-file" accept=".xlsx,.xls,.csv,.tsv,.json">
            </div>
            <p style="font-size:12px;color:var(--text3);margin-bottom:12px;">支持 .xlsx / .csv / .tsv / .json</p>
            <button class="btn btn-primary" id="btn-batch" onclick="startBatch()">开始搜索</button>
        </div>

        <!-- 状态和日志 -->
        <div class="card">
            <div class="status-bar">
                <div class="status-dot idle" id="status-dot"></div>
                <span id="status-text" style="font-size:14px;font-weight:500;">就绪</span>
            </div>
            <div class="log-box" id="log-box">等待开始...</div>
        </div>

        <!-- 结果 -->
        <div class="card hidden" id="result-panel">
            <h2>搜索结果</h2>
            <div class="results" id="result-cards"></div>
        </div>
    </div>

    <script>
        let currentTask = null;
        let pollTimer = null;

        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('single-panel').classList.toggle('hidden', tab !== 'single');
            document.getElementById('batch-panel').classList.toggle('hidden', tab !== 'batch');
            event.target.classList.add('active');
        }

        function setStatus(state, text) {
            const dot = document.getElementById('status-dot');
            dot.className = 'status-dot ' + state;
            document.getElementById('status-text').textContent = text;
        }

        function appendLog(msg) {
            const box = document.getElementById('log-box');
            let cls = '';
            if (msg.includes('✅')) cls = 'success';
            else if (msg.includes('🔴') || msg.includes('❌')) cls = 'error';
            else if (msg.includes('🟡') || msg.includes('⚠')) cls = 'warn';
            else if (msg.startsWith('  ') || msg.includes('──')) cls = 'dim';

            const span = document.createElement('span');
            span.className = cls;
            span.textContent = msg + '\\n';
            box.appendChild(span);
            box.scrollTop = box.scrollHeight;
        }

        function clearLog() {
            document.getElementById('log-box').innerHTML = '';
        }

        function startSingle() {
            const name = document.getElementById('landfill-name').value.trim();
            if (!name) { alert('请输入填埋场名称'); return; }
            const country = document.getElementById('landfill-country').value.trim() || '';

            clearLog();
            setStatus('running', '搜索中...');
            document.getElementById('btn-single').disabled = true;
            document.getElementById('result-panel').classList.add('hidden');

            fetch('/api/search/single', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name, country: country})
            })
            .then(r => r.json())
            .then(data => {
                currentTask = data.task_id;
                appendLog('任务已提交: ' + data.task_id);
                pollTimer = setInterval(pollStatus, 1000);
            });
        }

        function startBatch() {
            const fileInput = document.getElementById('data-file');
            if (!fileInput.files.length) { alert('请选择文件'); return; }

            clearLog();
            setStatus('running', '上传并搜索中...');
            document.getElementById('btn-batch').disabled = true;
            document.getElementById('result-panel').classList.add('hidden');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            fetch('/api/search/batch', { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                currentTask = data.task_id;
                appendLog('任务已提交: ' + data.task_id);
                pollTimer = setInterval(pollStatus, 1000);
            });
        }

        function pollStatus() {
            if (!currentTask) return;
            fetch('/api/task/' + currentTask)
            .then(r => r.json())
            .then(data => {
                // 追加新日志
                data.new_logs.forEach(appendLog);

                if (data.status === 'done') {
                    clearInterval(pollTimer);
                    setStatus('done', '✅ 搜索完成');
                    document.getElementById('btn-single').disabled = false;
                    document.getElementById('btn-batch').disabled = false;
                    showResults(data.results);
                } else if (data.status === 'error') {
                    clearInterval(pollTimer);
                    setStatus('error', '❌ 搜索失败');
                    document.getElementById('btn-single').disabled = false;
                    document.getElementById('btn-batch').disabled = false;
                }
            });
        }

        function showResults(results) {
            if (!results) return;
            const panel = document.getElementById('result-panel');
            const cards = document.getElementById('result-cards');
            panel.classList.remove('hidden');
            cards.innerHTML = '';

            const items = [
                {label: '可视化', value: results.html ? '<a href="/output/html/' + results.html_name + '" target="_blank">打开 HTML</a>' : '—'},
                {label: 'JSON 数据', value: results.json ? '<a href="/output/' + results.json_name + '" target="_blank">下载 JSON</a>' : '—'},
                {label: '日志', value: '<a href="/logs/" target="_blank">查看日志</a>'},
                {label: '检查报告', value: results.report ? '<a href="/output/' + results.report_name + '" target="_blank">查看报告</a>' : '—'},
            ];

            items.forEach(item => {
                cards.innerHTML += '<div class="result-card"><div class="label">' + item.label + '</div><div class="value">' + item.value + '</div></div>';
            });
        }
    </script>
</body>
</html>
"""


# ── API 路由 ──

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/output/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/output/html/<path:filename>")
def serve_html(filename):
    return send_from_directory(os.path.join(OUTPUT_DIR, "html"), filename)


@app.route("/logs/")
def serve_logs_index():
    files = sorted(Path(LOGS_DIR).glob("*.md"))
    links = "".join(f'<li><a href="/logs/{f.name}">{f.name}</a></li>' for f in files)
    return f"<h2>日志文件</h2><ul>{links}</ul>"


@app.route("/logs/<path:filename>")
def serve_logs(filename):
    return send_from_directory(LOGS_DIR, filename)


@app.route("/api/search/single", methods=["POST"])
def api_single():
    data = request.json
    name = data.get("name", "").strip()
    country = data.get("country", "").strip() or "Unknown"

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {"status": "running", "logs": [], "log_cursor": 0, "results": None}

    thread = threading.Thread(target=_run_single, args=(task_id, name, country), daemon=True)
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/search/batch", methods=["POST"])
def api_batch():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "no file"}), 400

    # 保存上传文件
    upload_dir = os.path.join(BASE_DIR, "data", "raw")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)

    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {"status": "running", "logs": [], "log_cursor": 0, "results": None}

    thread = threading.Thread(target=_run_batch, args=(task_id, file_path), daemon=True)
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/task/<task_id>")
def api_task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "not found"}), 404

    cursor = task["log_cursor"]
    new_logs = task["logs"][cursor:]
    task["log_cursor"] = len(task["logs"])

    return jsonify({
        "status": task["status"],
        "new_logs": new_logs,
        "results": task["results"],
    })


# ── 后台任务 ──

def _task_log(task_id, msg):
    if task_id in tasks:
        tasks[task_id]["logs"].append(msg)


def _run_single(task_id, name, country):
    try:
        code = name.upper().replace(" ", "_")[:10]

        temp_data = [{"code": 1, "name": name, "lat": None, "lng": None,
                      "country_code": code, "country": country}]
        temp_path = os.path.join(tempfile.gettempdir(), f"landfill_{code}.json")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(temp_data, f, ensure_ascii=False, indent=4)

        _task_log(task_id, f"搜索: {name} ({country})")
        _run_pipeline(task_id, temp_path, code)

    except Exception as e:
        _task_log(task_id, f"❌ 错误: {e}")
        tasks[task_id]["status"] = "error"


def _run_batch(task_id, file_path):
    try:
        code = Path(file_path).stem.upper()
        _task_log(task_id, f"文件: {file_path}")
        _run_pipeline(task_id, file_path, code)

    except Exception as e:
        _task_log(task_id, f"❌ 错误: {e}")
        tasks[task_id]["status"] = "error"


def _run_pipeline(task_id, input_path, code):
    """执行搜索 + Pipeline。"""
    def callback(level, msg):
        _task_log(task_id, msg)

    try:
        # 搜索
        from src.search.scrape_runner import run_scrape
        _task_log(task_id, "▸ 开始自动搜索...")
        run_scrape(input_path, output_dir=OUTPUT_DIR, headless=False,
                   batch_size=10, engines="google,scholar,maps", num_workers=1)

        # Pipeline
        from main import run_pipeline
        _task_log(task_id, "▸ 运行 Pipeline（检查+生成）...")
        run_pipeline(input_path, output_dir=OUTPUT_DIR)

        # 结果
        html_name = f"{code}.html"
        json_name = f"{code}.json"
        report_name = f"{code}_check_report.md"

        html_path = os.path.join(OUTPUT_DIR, "html", html_name)
        json_path = os.path.join(OUTPUT_DIR, json_name)
        report_path = os.path.join(OUTPUT_DIR, report_name)

        tasks[task_id]["results"] = {
            "html": os.path.exists(html_path),
            "html_name": html_name,
            "json": os.path.exists(json_path),
            "json_name": json_name,
            "report": os.path.exists(report_path),
            "report_name": report_name,
        }
        tasks[task_id]["status"] = "done"
        _task_log(task_id, "✅ 搜索完成")

    except Exception as e:
        _task_log(task_id, f"❌ Pipeline 错误: {e}")
        tasks[task_id]["status"] = "error"


# ── 启动 ──

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Landfill Search — Web UI")
    print("  访问: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", port=8000, debug=False)
