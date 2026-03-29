# 日志目录说明

所有 Pipeline 和搜索过程的运行日志自动保存在本目录。

## 日志文件

| 文件 | 内容 | 何时生成 |
|------|------|---------|
| `{CODE}_pipeline.md` | Pipeline 完整日志 | `python main.py` |
| `{CODE}_scrape_pipeline.md` | 搜索过程日志 | `scrape_runner` |
| `{CODE}_errors.md` | 仅错误和警告 | 有错误时自动生成 |

`{CODE}` 为国家代码（如 `ITA`）。

## 日志格式

### 状态标记
- `✅` 成功
- **`🔴` 错误**（加粗标红）— 必须修正
- `🟡` 警告 — 需人工确认
- `📊` 进度 — 搜索进度和 ETA

### 时间戳
每条日志带 `HH:MM:SS` 时间戳：
```
- `14:23:05` ✅ Cupello: 4/5 项
- `14:23:48` 🔴 Tricarico: start_year > final_year
```

### 进度条
搜索过程显示进度和预计剩余时间：
```
📊 [████████░░░░] 45/179 (25.1%) | ETA: 1h 20m | 58s/个
```

### 折叠详情
每个填埋场的搜索结果以可折叠格式保存，点击展开：
```markdown
<details><summary>Cupello: 4/5 项</summary>
- landfill_type: sanitary landfill (来源: ...)
- has_gas_collection: yes (来源: ...)
</details>
```

### Worker 标识
多进程搜索时带 Worker 标识：
```
[W0:Chrome] 搜索: Malagrotta
[W1:WebKit] 搜索: Bellolampo
```

## 查看方式

```bash
# VS Code 打开（推荐，支持 Markdown 预览和折叠）
code logs/ITA_pipeline.md

# 快速看错误
cat logs/ITA_errors.md

# 终端查看
less logs/ITA_pipeline.md
```

## 清理

日志文件不会自动清理。如需清理：
```bash
rm logs/*.md    # 删除所有日志
```

无错误/警告时，`_errors.md` 文件会自动删除，不会留空文件。
