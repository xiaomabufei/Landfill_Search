"""总结模块：生成 HTML 地图可视化和统计展示页面。"""

from typing import List, Dict
import json
from pathlib import Path


def generate_html(json_path: str, output_path: str):
    """读取 JSON 数据，生成带地图和统计的 HTML 页面。"""

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    country = data["country"]
    code = data["country_code"]
    version = data.get("data_version", "N/A")
    generated = data.get("generated_at", "N/A")
    landfills = data["landfills"]
    total = len(landfills)

    # 统计
    type_dump = sum(1 for lf in landfills if lf.get("landfill_type") == "dump")
    type_sanitary = sum(1 for lf in landfills if lf.get("landfill_type") == "sanitary landfill")
    type_unknown = total - type_dump - type_sanitary

    gc_yes = sum(1 for lf in landfills if lf.get("has_gas_collection") == "yes")
    gc_no = sum(1 for lf in landfills if lf.get("has_gas_collection") == "no")
    gc_unknown = total - gc_yes - gc_no

    tech_flaring = sum(1 for lf in landfills if lf.get("gas_collection_technology") and "flaring" in lf["gas_collection_technology"])
    tech_elec = sum(1 for lf in landfills if lf.get("gas_collection_technology") and "electrification" in lf["gas_collection_technology"])
    tech_puri = sum(1 for lf in landfills if lf.get("gas_collection_technology") and "purification" in lf["gas_collection_technology"])
    tech_none = total - tech_flaring - tech_elec - tech_puri

    # 完整率
    fields_check = ["landfill_type", "has_gas_collection", "gas_collection_technology",
                     "gas_collection_rate", "start_year", "final_year", "gas_collection_start_year"]
    filled_count = 0
    total_fields = total * len(fields_check)
    for lf in landfills:
        for f in fields_check:
            if lf.get(f) is not None:
                filled_count += 1
    completeness = round(filled_count / total_fields * 100, 1) if total_fields > 0 else 0

    # 计算地图中心
    lats = [lf["location"]["lat"] for lf in landfills if lf["location"]["lat"]]
    lngs = [lf["location"]["lng"] for lf in landfills if lf["location"]["lng"]]
    center_lat = sum(lats) / len(lats) if lats else 42.0
    center_lng = sum(lngs) / len(lngs) if lngs else 14.0

    landfills_json = json.dumps(landfills, ensure_ascii=False)

    html = """<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>""" + f"{country} ({code})" + """ — Landfill Data</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1a56db;
            --primary-light: #e8effc;
            --danger: #dc2626;
            --success: #16a34a;
            --warning: #f59e0b;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-500: #6b7280;
            --gray-700: #374151;
            --gray-900: #111827;
            --radius: 12px;
            --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.05), 0 2px 4px rgba(0,0,0,0.03);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', -apple-system, sans-serif; background: var(--gray-50); color: var(--gray-900); line-height: 1.5; }

        /* Header */
        .header { background: var(--gray-900); color: white; padding: 32px 0; }
        .header-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }
        .header-meta { font-size: 13px; color: var(--gray-300); text-align: right; }
        .header-meta span { display: block; }

        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }

        /* Stats */
        .stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 28px; }
        .stat-card { background: white; border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow); border: 1px solid var(--gray-200); }
        .stat-card .label { font-size: 12px; color: var(--gray-500); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
        .stat-card .number { font-size: 32px; font-weight: 700; color: var(--gray-900); margin-top: 4px; }
        .stat-card .sub { font-size: 12px; color: var(--gray-500); margin-top: 2px; }

        /* Section */
        .section { margin-bottom: 28px; }
        .section-title { font-size: 16px; font-weight: 600; color: var(--gray-700); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
        .section-title::before { content: ''; width: 4px; height: 20px; background: var(--primary); border-radius: 2px; }

        /* Map */
        #map { height: 520px; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--gray-200); }
        .legend { display: flex; gap: 20px; margin-top: 10px; font-size: 13px; color: var(--gray-500); }
        .legend-item { display: flex; align-items: center; gap: 6px; }
        .legend-dot { width: 12px; height: 12px; border-radius: 50%; }

        /* Charts */
        .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .chart-card { background: white; border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow); border: 1px solid var(--gray-200); }
        .chart-card h3 { font-size: 14px; font-weight: 600; color: var(--gray-700); margin-bottom: 16px; }

        /* Table */
        .table-wrap { background: white; border-radius: var(--radius); box-shadow: var(--shadow); border: 1px solid var(--gray-200); overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th { background: var(--gray-50); color: var(--gray-500); padding: 10px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; border-bottom: 1px solid var(--gray-200); white-space: nowrap; }
        td { padding: 12px 14px; border-bottom: 1px solid var(--gray-100); font-size: 13px; color: var(--gray-700); }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: var(--primary-light); }
        td.name-cell { font-weight: 600; color: var(--gray-900); }
        .missing { color: var(--gray-300); }

        /* Badges */
        .badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: 0.2px; }
        .badge-sanitary { background: #dbeafe; color: #1e40af; }
        .badge-dump { background: #fee2e2; color: #991b1b; }
        .badge-yes { background: #dcfce7; color: #166534; }
        .badge-no { background: #fee2e2; color: #991b1b; }
        .badge-null { background: var(--gray-100); color: var(--gray-500); }

        /* Popup */
        .leaflet-popup-content-wrapper { border-radius: 10px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important; }
        .leaflet-popup-content { margin: 14px 16px !important; font-family: 'Inter', sans-serif !important; }
        .popup-title { font-size: 15px; font-weight: 700; color: var(--gray-900); margin-bottom: 8px; }
        .popup-row { font-size: 12px; color: var(--gray-500); padding: 3px 0; display: flex; gap: 6px; }
        .popup-row strong { color: var(--gray-700); min-width: 50px; }
        .popup-refs { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--gray-200); }
        .popup-refs a { font-size: 11px; color: var(--primary); text-decoration: none; margin-right: 8px; }
        .popup-refs a:hover { text-decoration: underline; }

        .footer { text-align: center; padding: 24px; color: var(--gray-300); font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-inner">
            <h1>""" + f"{country}" + """ — Landfill Database</h1>
            <div class="header-meta">
                <span>Version """ + version + """</span>
                <span>""" + generated + """</span>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="label">Total</div>
                <div class="number">""" + str(total) + """</div>
                <div class="sub">landfills</div>
            </div>
            <div class="stat-card">
                <div class="label">Gas Collection</div>
                <div class="number">""" + str(gc_yes) + """</div>
                <div class="sub">of """ + str(total) + """ have gas recovery</div>
            </div>
            <div class="stat-card">
                <div class="label">Sanitary</div>
                <div class="number">""" + str(type_sanitary) + """</div>
                <div class="sub">sanitary landfills</div>
            </div>
            <div class="stat-card">
                <div class="label">Dump</div>
                <div class="number">""" + str(type_dump) + """</div>
                <div class="sub">dump sites</div>
            </div>
            <div class="stat-card">
                <div class="label">Completeness</div>
                <div class="number">""" + str(completeness) + """<span style="font-size:18px">%</span></div>
                <div class="sub">data filled</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Map Distribution</div>
            <div id="map"></div>
            <div class="legend">
                <div class="legend-item"><div class="legend-dot" style="background:#3b82f6;"></div> Sanitary Landfill</div>
                <div class="legend-item"><div class="legend-dot" style="background:#ef4444;"></div> Dump</div>
                <div class="legend-item"><div class="legend-dot" style="background:#9ca3af;"></div> Unknown</div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Statistics</div>
            <div class="charts">
                <div class="chart-card">
                    <h3>Landfill Type</h3>
                    <canvas id="typeChart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Gas Collection Technology</h3>
                    <canvas id="techChart"></canvas>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Data Table</div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>ID</th><th>Name</th><th>Type</th><th>Gas</th>
                            <th>Technology</th><th>Rate</th><th>Start</th><th>Close</th><th>Gas Start</th>
                        </tr>
                    </thead>
                    <tbody id="dataTable"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="footer">Landfill Search Project &middot; """ + code + """ &middot; """ + version + """</div>

    <script>
        var landfills = """ + landfills_json + """;
        var centerLat = """ + str(center_lat) + """;
        var centerLng = """ + str(center_lng) + """;

        // Map — use CartoDB tiles (no referer restriction)
        var map = L.map('map').setView([centerLat, centerLng], 6);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(map);

        // Markers
        landfills.forEach(function(lf) {
            var lat = lf.location.lat, lng = lf.location.lng;
            if (!lat || !lng) return;

            var t = lf.landfill_type || 'unknown';
            var color = t === 'dump' ? '#ef4444' : t === 'sanitary landfill' ? '#3b82f6' : '#9ca3af';

            var popup = '<div class="popup-title">' + lf.name + '</div>';
            popup += '<div class="popup-row"><strong>Type</strong> ' + (lf.landfill_type || '-') + '</div>';
            popup += '<div class="popup-row"><strong>Gas</strong> ' + (lf.has_gas_collection || '-') + '</div>';
            popup += '<div class="popup-row"><strong>Tech</strong> ' + (lf.gas_collection_technology || '-') + '</div>';
            popup += '<div class="popup-row"><strong>Years</strong> ' + (lf.start_year || '?') + ' ~ ' + (lf.final_year || 'open') + '</div>';

            var refs = [
                {d: lf.landfill_type_ref, l: 'Type'},
                {d: lf.has_gas_collection_ref, l: 'Gas'},
                {d: lf.start_year_ref, l: 'Start'},
                {d: lf.final_year_ref, l: 'Close'}
            ];
            var hasRef = refs.some(function(r){ return r.d && r.d.url; });
            if (hasRef) {
                popup += '<div class="popup-refs">';
                refs.forEach(function(r) {
                    if (r.d && r.d.url) popup += '<a href="' + r.d.url + '" target="_blank">[' + r.l + ']</a>';
                });
                popup += '</div>';
            }

            L.circleMarker([lat, lng], {
                radius: 8, fillColor: color, color: '#fff',
                weight: 2, opacity: 1, fillOpacity: 0.9
            }).addTo(map).bindPopup(popup, {maxWidth: 280});
        });

        // Table
        var tbody = document.getElementById('dataTable');
        landfills.forEach(function(lf) {
            var tr = document.createElement('tr');
            function cell(val, type) {
                if (val === null || val === undefined) return '<span class="missing">—</span>';
                if (type === 'gc') return '<span class="badge ' + (val==='yes'?'badge-yes':'badge-no') + '">' + val + '</span>';
                if (type === 'type') return '<span class="badge ' + (val==='dump'?'badge-dump':'badge-sanitary') + '">' + val + '</span>';
                return val;
            }
            tr.innerHTML = '<td>' + lf.id + '</td>'
                + '<td class="name-cell">' + lf.name + '</td>'
                + '<td>' + cell(lf.landfill_type, 'type') + '</td>'
                + '<td>' + cell(lf.has_gas_collection, 'gc') + '</td>'
                + '<td>' + cell(lf.gas_collection_technology) + '</td>'
                + '<td>' + cell(lf.gas_collection_rate) + '</td>'
                + '<td>' + cell(lf.start_year) + '</td>'
                + '<td>' + cell(lf.final_year) + '</td>'
                + '<td>' + cell(lf.gas_collection_start_year) + '</td>';
            tbody.appendChild(tr);
        });

        // Type chart
        new Chart(document.getElementById('typeChart'), {
            type: 'doughnut',
            data: {
                labels: ['Sanitary Landfill', 'Dump', 'Unknown'],
                datasets: [{
                    data: [""" + str(type_sanitary) + "," + str(type_dump) + "," + str(type_unknown) + """],
                    backgroundColor: ['#3b82f6', '#ef4444', '#d1d5db'],
                    borderWidth: 0, hoverOffset: 6
                }]
            },
            options: {
                cutout: '60%',
                plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'circle', font: {size: 12} } } }
            }
        });

        // Tech chart
        new Chart(document.getElementById('techChart'), {
            type: 'bar',
            data: {
                labels: ['Flaring', 'Electrification', 'Purification', 'Unknown'],
                datasets: [{
                    data: [""" + str(tech_flaring) + "," + str(tech_elec) + "," + str(tech_puri) + "," + str(tech_none) + """],
                    backgroundColor: ['#f97316', '#3b82f6', '#22c55e', '#d1d5db'],
                    borderRadius: 6, borderSkipped: false, barPercentage: 0.6
                }]
            },
            options: {
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1, font: {size: 12} }, grid: { color: '#f3f4f6' } },
                    x: { grid: { display: false }, ticks: { font: {size: 12} } }
                },
                plugins: { legend: { display: false } }
            }
        });
    </script>
</body>
</html>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML 已生成: {output_path}")


if __name__ == "__main__":
    json_path = Path(__file__).parent.parent.parent / "output" / "ITA.json"
    output_path = Path(__file__).parent.parent.parent / "output" / "html" / "ITA.html"
    generate_html(str(json_path), str(output_path))
