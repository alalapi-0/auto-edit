# Auto Mograph Bot

Auto Mograph Bot 提供一套可扩展的本地短视频自动化流水线脚手架，涵盖文案采样、Stable Diffusion 文本生图、AnimateDiff / Stable Video Diffusion 图生视频、FFmpeg 后期处理以及草稿上传模块。所有代码均以中文注释，便于快速二次开发。

## 功能特性

- **配置中心**：通过 `.env` 与 `configs/default.yaml` 管理分辨率、帧率、模型路径、上传 Provider 等参数。
- **文案池管理**：内置 20+ 主题+风格组合，支持去重、敏感词/广告词过滤、黑名单与标题/描述/标签生成。
- **模型接入**：提供 diffusers 本地推理与 Stable Diffusion WebUI API 两种文本生图后端；图生视频可在 AnimateDiff 与 Stable Video Diffusion 之间切换。
- **视频后期**：使用 FFmpeg 完成竖屏 1080×1920 适配、字幕/水印开关、BGM 混音、封面帧导出。
- **批量调度**：支持批量生成、失败重试、冷却时间、产物 JSONL 索引与哈希去重。
- **上传抽象**：预置 API、Web 自动化、Appium 三类草稿 Provider（均为占位实现），并保留 uploader 接口以供后续扩展真实上传逻辑。
- **安全合规**：在文案侧做敏感词过滤与广告用语拦截，提醒用户遵守平台政策。

## 环境准备

1. 安装 Python 3.10 及以上版本。
2. 安装 FFmpeg，并确保可执行文件位于 `PATH` 中（或在 `.env` 中设置 `FFMPEG_PATH`）。
3. 克隆仓库后进入 `auto-mograph-bot/` 目录。
4. 安装依赖：
   ```bash
   python -m pip install -r requirements.txt
   ```
5. 根据需要安装 Playwright 浏览器内核：
   ```bash
   playwright install
   ```

> **提示**：当前仓库仅提供最小可运行的占位实现；要获得真实的 AI 生成效果，请自行准备本地模型权重（放置于 `models/`）或连接现有的 Stable Diffusion WebUI。所有模型文件禁止提交至版本库。

## 配置说明

## 安全配置

- 浏览器登录态与 Token 需要通过 UI 中的“密钥”页面导入，首次导入可以使用临时的明文 `storage_state` JSON 文件。
- 导入完成后请立即删除原始 JSON 文件，密钥会写入 `secrets/.vault.enc` 并使用主密码加密。
- `secrets/.vault.enc` 为加密后的密钥库文件，仅包含密文与元数据，请勿上传或共享该文件内容。
- 项目禁止提交任何二进制产物（模型、可执行文件、截图等），密钥示例和真实 Cookie/Token 也不可写入仓库。
- UI 状态栏会显示各平台登录态的剩余有效天数，提醒及时更新。

### `.env`

复制 `.env.example` 为 `.env`，根据实际环境填写：

- `SD_WEBUI_URL`、`SD_WEBUI_TOKEN`：连接 Stable Diffusion WebUI API 使用。
- `SD_MODEL_PATH`、`ANIMATEDIFF_MODEL_PATH` 等：本地模型路径。
- `UPLOADER_COOKIE_PATH`、`UPLOADER_API_TOKEN`、`APPIUM_SERVER` 等：对应上传 Provider 所需的敏感凭证。

`.env` 会在运行时自动加载，不会被提交到仓库。

### `configs/default.yaml`

示例配置包含以下核心模块：

- `video`：分辨率（1080×1920）、帧率（24fps）、时长（6s）、CRF、封面导出等。
- `sd` / `animate`：后端选择、本地模型路径、推理参数（步数、CFG、种子等）。
- `prompts`：额外文案/风格/标签、黑名单、敏感词列表、标题/描述/标签长度限制。
- `audio`：是否自动混入 BGM、BGM 目录、音量归一化开关。
- `scheduler`：批量参数（`batch_size`、`concurrency`、`max_retries`、`cooldown_sec`、索引路径、日志目录）。当前骨架默认串行执行。
- `uploader`：`provider` 取值 `none` / `web` / `appium` / `api`，以及平台、可见性、Cookie 路径、Appium 服务器等。
- `safety` / `runtime`：敏感词检测开关、全局随机种子、是否 Dry Run。

可以新增自定义字段，运行时会保留在 `PipelineConfig.raw_data` 中供业务读取。

## 快速运行

1. 准备好 `.env` 与 `configs/default.yaml`。
2. 执行：
   ```bash
   python -m runner.cli --count 1
   ```
3. 程序将在 `outputs/` 下生成形如 `20240101_123456_标题-slug.mp4` 的 6 秒竖屏占位视频，并追加一条索引到 `outputs/index.jsonl`。

> **占位说明**：若未接入真实模型，`txt2img` 与 `img2vid` 会写出 JSON 元数据并调用 FFmpeg 生成纯色占位视频，以保证流水线可跑通。接入真实模型时请在对应后端中替换推理逻辑。

## 文案与安全过滤

- `src/prompts/pool.py` 内置 20+ 主题与多组风格、标签，支持从配置文件补充。
- 通过 `blacklist_topics` 和 `sensitive_words` 阻止违规文案；检测到敏感词或广告词会重新抽取，重试超过 10 次会抛出异常。
- 生成的标题（≤30 字）、描述（≤120 字）与标签（≤5 个）会附带到上传元数据中。

## 批量生成与索引

- `runner/scheduler.py` 负责批量调度、失败重试与冷却时间控制。
- 每个成功任务都会记录到 `outputs/index.jsonl`，包含 prompt、seed、模型后端、产物路径、哈希及上传结果。
- 若检测到重复文件哈希，会跳过索引写入，避免重复记录。

## 上传 Provider 配置

所有 Provider 均通过 `uploader.router` 路由，返回 `DraftResult`（仅模拟）。请根据需求二次实现真实上传逻辑，并关注平台风控政策。

### Provider=api（官方/半官方接口）

- 文件：`src/uploader/providers/tiktok_like_api.py`
- 需要在 `configs/default.yaml` 设置 `uploader.provider: "api"`，并提供 `uploader.extra.api_base` 与 `.env` 中的 `UPLOADER_API_TOKEN`。
- 代码仅示范参数构建，未实际发起请求。请按照官方文档实现鉴权、分片上传与频控。

### Provider=web（Playwright 自动化）

- 文件：`src/uploader/providers/xiaohongshu_web.py`
- 准备步骤：
  1. 在浏览器中登录创作平台，导出 Cookie（JSON）并保存到 `.env` 中 `UPLOADER_COOKIE_PATH` 指向的路径。
  2. 首次运行前执行 `playwright install` 安装浏览器内核。
  3. 配置 `uploader.visibility`（如 `private`）与目标平台地址。
- 运行时会加载 Cookie，打开创作页并模拟上传操作，同时在 `outputs/logs/` 留下截图与 HAR 轨迹，便于排查风控问题。
- 请勿尝试绕过验证码或其他安全策略，避免账号风险。

### Provider=appium（移动端自动化）

- 文件：`src/uploader/providers/android_appium.py`
- 需要在 `.env` 中提供 `APPIUM_SERVER`、`APPIUM_DEVICE_NAME` 等参数，并在 YAML `uploader.extra` 里配置 App 包名、Activity 等信息。
- 代码仅打印核心步骤，需结合实际 App UI 元素自行补全点击与输入逻辑。
- 建议使用 Android 模拟器或真机，确保视频分辨率与 1080×1920 对齐，以免在移动端裁切。

> **安全提醒**：官方对“直接发草稿/投稿”的接口权限非常严格，请确保账号已获授权且遵守平台发布规范。频繁调用可能触发风控，建议合理设置 `scheduler.cooldown_sec` 与重试次数。

## 法律与合规

- 模型权重、LoRA、VAE 等需遵循各自的开源或商业许可，请勿擅自分发。
- 生成内容需遵守当地法律法规及平台社区规范，避免侵权、虚假宣传、违规广告等问题。
- 使用 Cookie、Token 等敏感信息时需妥善保管，不要提交到版本库，也不要在不可信环境运行上传脚本。

## 故障排查

| 问题 | 可能原因 | 解决方案 |
| --- | --- | --- |
| FFmpeg 找不到 | 系统未安装或未加入 PATH | 安装 FFmpeg，或在 `.env` 设置 `FFMPEG_PATH` |
| CUDA OOM / 显存不足 | 模型尺寸过大或并发度过高 | 降低分辨率、减少 `scheduler.concurrency`、启用 `runtime.dry_run` |
| Playwright 启动失败 | 未安装浏览器内核 | 执行 `playwright install`，或根据提示安装依赖 |
| Appium 连接失败 | 服务器地址或模拟器未启动 | 检查 `APPIUM_SERVER`、ADB 端口、设备连接状态 |
| 文案抽取失败 | 黑名单/敏感词过于严格 | 放宽关键词配置或补充文案池 |

## 后续扩展建议

- 在 `src/uploader/interfaces.py` 的 `Uploader` 协议基础上实现真实上传逻辑，并结合指数退避、频控策略。
- 在 `src/runner/scheduler.py` 中完善并发执行、显存监控与失败截图收集。
- `uploader` 模块已预留“上传草稿”三种 Provider，后续可根据平台更新完善参数校验与异常处理。

如需新增“上传草稿”功能以外的模块，可在 `src/uploader/` 下新建子包，并在 README 中补充使用说明。
