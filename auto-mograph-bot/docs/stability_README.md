# 稳定性与可观测性说明

本文档介绍 Stable Diffusion/FFmpeg 调用的重试策略、错误分类及结构化日志字段，帮助在网络抖动或依赖异常时快速定位问题。

## 退避重试策略

- **指数退避**：首轮尝试失败后，等待时间按 `delay *= backoff_factor` 成长，默认 `1s → 2s → 4s`。
- **随机抖动**：为避免雪崩，在每次等待前额外添加 `0 ~ jitter_ms` 的随机抖动（毫秒）。
- **最大尝试次数**：`retry.max_attempts` 控制包含首次调用在内的总尝试次数，默认 3 次。
- **可配置性**：上述参数均可在 `configs/default.yaml` 的 `retry` 段中修改；FFmpeg 可通过 `retry.ffmpeg.enabled` 和 `retry.ffmpeg.retryable_exit_codes` 进一步限制重试范围。

## 错误分类

### Stable Diffusion（文本生图/图生视频）

| 分类 | 触发条件 | 建议 hint |
| --- | --- | --- |
| `timeout` | 调用超时或响应中包含 `timeout` | 检查网络连通性或增加超时时间 |
| `conn_error` | 无法建立连接、DNS 失败、连接拒绝 | 确认 SD WebUI 地址/端口可达 |
| `http_5xx` | WebUI 返回 5xx | 检查 WebUI 服务端日志并重启 |
| `rate_limited` | 返回 429 | 降低并发或增加请求间隔 |
| `bad_request` | WebUI 返回 4xx（非 401/429） | 检查提示词和参数合法性 |
| `auth_error` | 401/鉴权失败 | 核对 Token 或鉴权配置 |
| `oom` | 消息含 `out of memory`/`CUDA` | 降低分辨率或 batch size |
| `unknown` | 其余未识别异常 | 查看 `pipeline.jsonl` 中的 traceback |

### FFmpeg 执行

| 分类 | 触发条件 | 建议 hint |
| --- | --- | --- |
| `no_ffmpeg` | 无可执行文件或 `command not found` | 安装 FFmpeg 并添加到 PATH |
| `file_not_found` | `No such file or directory` | 核对输入/输出路径 |
| `disk_full` | `No space left on device` 等 | 清理磁盘或切换输出目录 |
| `permission` | `Permission denied` | 检查文件/目录权限 |
| `codec_missing` | `codec not found`/`unknown encoder` | 安装编解码器或修改参数 |
| `resource_busy` | `resource busy`/`temporarily unavailable` | 确保目标文件未被占用 |
| `broken_pipe` | `Broken pipe`/`EPIPE` | 检查上游数据管道 |
| `timeout` | 包含 `timed out` | 检查 IO/网络或提高超时 |
| `io_error` | `Input/output error` | 检查磁盘健康状况 |
| `unknown` | 其他错误 | 查看完整 stderr |

配置中列出的退出码（默认 `1`、`255`）或分类为 `timeout`/`resource_busy`/`broken_pipe`/`io_error` 时会触发自动重试。

## 结构化日志 (`outputs/logs/pipeline.jsonl`)

每行是一条 JSON 记录，核心字段说明：

- `event`：事件名称，如 `sd_call_start`、`ffmpeg_fail`、`upload_success`。
- `ts`：UNIX 时间戳（秒）。
- `elapsed_ms`：事件耗时（毫秒），若适用。
- `category`：错误分类（仅失败事件）。
- `hint`：针对错误的修复建议。
- `command`/`fn`/`provider` 等上下文字段：指示命令、函数名或上传渠道。
- `traceback`：异常堆栈，仅在 `log_exception` 中出现。
- `stderr`：FFmpeg 失败时截断后的标准错误文本。

### 快速排查建议

1. **定位异常**：搜索 `ffmpeg_fail`、`sd_call_fail` 或 `upload_fail`，查看 `category` 与 `hint`。
2. **追踪重试**：同一事件的 `attempt` 与 `max_attempts` 可评估重试次数。
3. **对比耗时**：`elapsed_ms` 帮助确认问题集中在哪个环节。
4. **关联上下文**：结合 `seed`、`backend`、`file` 等字段将日志与具体任务关联。

合理配置重试与观察日志可以显著提升链路在网络抖动、磁盘异常等情况下的自愈能力与可诊断性。
