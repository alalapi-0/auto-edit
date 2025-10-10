# 配置中心与 Profile 使用指南

本文档说明如何使用统一配置中心、抽样回退策略以及 Profile 导入/导出流程。所有示例均为纯文本 YAML，不会生成任何二进制或媒体文件。

## 统一配置中心

- 配置中心位于 `src/config_center/center.py`，由 `ConfigCenter` 负责加载、合并与校验配置。
- 加载顺序：
  1. `configs/default.yaml`
  2. 可选的覆盖文件（例如 `configs/mvp.yaml` 或导入的 Profile）
  3. 环境变量（通过 `.env` 或进程环境传入）
- 配置被验证后会冻结成只读视图供 CLI 与 GUI 同时使用，防止运行时被意外修改。
- 通过 `src/config.py` 中的 `load_config`、`get_config_center`、`get_config_view` 可以在任意模块获取一致的配置数据。

## 抽样失败统计与回退

`configs/default.yaml` 中新增 `sampling` 段落，用于定义抽样统计与回退策略：

```yaml
sampling:
  max_retries: 10
  stats_log: true
  fallback:
    enabled: true
    title: "今天也要加油"
    description: "保持创作与节奏，见证每天的小进步。"
    tags: ["日常", "励志", "记录"]
    prompt_text: "清新剪贴风, 竖屏, 简约背景, 主角置中"
  blacklist: []
  safe_words: ["温暖", "可爱", "元气"]
```

- `max_retries`：文案采样的最大尝试次数。
- `stats_log`：为 `true` 时成功样本和回退事件都会写入 `outputs/logs/pipeline.jsonl`。
- `fallback.enabled`：达到阈值后是否启用安全默认文案。
- `fallback` 内的标题、描述、标签、提示词都会在需要时作为兜底内容，并自动注入 `safe_words`。
- `blacklist`、`safe_words` 可在运行时追加，便于 GUI/CLI 统一维护。

结构化日志事件：

- `prompt_sample_success`：采样成功，附带统计字段。
- `prompt_fallback_used`：触发回退，包含失败原因与最终文案。
- `prompt_fallback_trimmed`：当兜底文案因超长被截断时记录。
- `prompt_sample_exhausted`：达到阈值但未启用回退时的错误信息。

所有日志都会写入纯文本 JSONL 文件 `outputs/logs/pipeline.jsonl`，方便后续统计。

## Profile 导入与导出

- `profiles.dir` 字段定义 Profile 存放目录，默认 `profiles/`。
- GUI 配置编辑器与 CLI 均通过配置中心读写 Profile：
  - **导出**：GUI 中点击“导出 Profile”按钮，或调用 `ConfigCenter.export_profile(name, path)`，会将当前合并后的配置保存为 `{profile: {name}, config: ...}` 结构的 YAML。
  - **导入**：GUI 中点击“导入 Profile”，或调用 `ConfigCenter.import_profile(path)`。配置中心会将 Profile 与默认配置合并后写入 `configs/NAME.yaml`，并立即刷新全局视图。
- 导入/导出的 Profile 均为纯文本 YAML 文件，可通过版本管理或外部工具编辑。

## 在 CLI 中使用

```python
from pathlib import Path
from src.config import load_config

config = load_config(Path("configs/default.yaml"))
print(config.video.width)
```

- `load_config` 始终走配置中心逻辑，确保 CLI、批处理脚本与 GUI 共享同一份配置。
- 若需要查看只读配置，可调用 `from src.config import get_config_view` 获取冻结后的字典。

## 在 GUI 中使用

- `ui/components/views/config_editor.py` 已接入配置中心，支持配置保存前校验与 Profile 导入/导出。
- GUI 保存配置后会立即调用配置中心刷新，使 CLI/后台任务能够读取到最新的 YAML。

## 注意事项

- 项目不会生成任何二进制、模型或媒体样例文件，所有配置/日志均为纯文本。
- 导入外部 Profile 时请确认其来源可信，避免覆盖敏感字段。
- 结构化日志文件可能包含统计数据，请在分享前做脱敏处理。
