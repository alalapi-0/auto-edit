# Auto Mograph 桌面 UI 使用说明

> 首版 UI 以“可用、结构清晰”为目标，样式为基础暗色主题。后续可根据需求进一步美化与扩展。

## 安装依赖

```bash
pip install -r requirements.txt
```

> 如果使用 Poetry，请执行 `poetry install` 并确保可选依赖也被安装。

新增依赖：PySide6、keyring、SQLAlchemy、PyMySQL、alembic、requests、pydantic、PyYAML、cryptography。

## 启动 UI

```bash
python -m ui.app
```

首启将弹出引导向导，完成基础环境检测（FFmpeg、Playwright）、数据库 URL 填写与 storage_state 导入。若需跳过向导，可在首启时添加 `--no-wizard` 参数。

## 功能总览

- **Profile 管理**：窗口右上角可切换配置 Profile，支持新建与“另存为”。Profile 文件保存在 `profiles/` 下。
- **Dashboard**：快速查看磁盘空间、数据库状态、FFmpeg/Playwright 检测，并可一键触发生成或模拟上传。
- **生成参数**：编辑分辨率、FPS、时长、CRF、动作预设、种子、文案与字体路径，并写入 `profiles/*.yaml`。
- **上传配置**：选择上传平台与 Provider，配置 storage_state 路径或 Appium 连接，并可执行模拟上传测试。
- **数据库**：切换数据库类型、测试连接、初始化基础表结构。
- **VPS Provider**：目前支持本地与占位 Provider，可输入伪 API Key 并演示创建/销毁流程。
- **密钥管理**：通过加密密钥库统一保存浏览器登录态，支持 Fernet 本地加密与系统 Keyring 两种后端，可设置主密码并查看有效期倒计时。
- **配置文件编辑**：直接查看、编辑 `configs/*.yaml`，并进行 schema 校验。
- **运行日志**：实时查看流水线输出，可搜索、清空、导出。
- **历史记录**：读取数据库中最新的 Runs/Uploads 记录，支持双击查看详情。

## 一键生成流程

1. 在 Dashboard 中点击“测试数据库”“测试 FFmpeg”“测试登录态”确认环境就绪。
2. 根据需求调整“生成参数”“上传配置”“VPS Provider”“密钥”等页面的设置。
3. 返回 Dashboard，点击“开始生成”。流水线运行日志会实时显示在“运行日志”页面。
4. 生成结束后，切换至“历史记录”查看最新 Run/Upload 的状态与产物信息。

## 数据与安全

- 所有敏感信息默认保存在 `secrets/` 目录或系统 keyring。`secrets/` 已加入 `.gitignore`。
- 本地加密采用 Fernet（基于 cryptography），首次使用需设置主密码。
- 日志输出会屏蔽敏感字段；如需排查，可使用“导出”按钮生成脱敏日志文本。

### 密钥管理流程

1. 打开“密钥”页面，选择 Fernet 或系统 Keyring 作为存储后端，并设置主密码进行解锁。
2. 通过“导入登录态”按钮选择浏览器导出的 `storage_state` JSON 文件，设置有效期（默认 30 天）。
3. 导入成功后，原始 JSON 文件会被安全删除，条目将显示在列表中，并标注剩余天数与是否过期。
4. 需要更新时，可重新导入同名条目或使用“删除所选”按钮清空旧登录态。

> 提示：运行 UI 后可在此处补充一张“主密码设置”界面截图，以便团队成员参考。

## 后续规划

- 扩展 VPS Provider 接入真实云厂商 API。
- 打通上传流程，与真实 Playwright/Appium 会话联动。
- 丰富日志检索、任务调度与监控能力。
- 优化 UI 主题与布局，适配高 DPI 屏幕。

欢迎在 `docs/` 补充截图与使用指南，或根据业务需求扩展模块。
