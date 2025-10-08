# Auto Mograph Bot

Auto Mograph Bot 提供一个用于自动化文案生成、图像合成、视频生成与后期处理的流水线脚手架。

## 功能概览
- 加载 `.env` 与 YAML 配置，统一管理画面参数、模型路径等。
- 提供文案、风格、标签池管理，支持去重与随机抽样。
- 结合本地 Stable Diffusion 文本生图与 AnimateDiff/Stable Video Diffusion 等视频模型。
- 封装常见的 FFmpeg 处理流程，包括拼接、裁切、加速与封面帧合成。
- 支持竖屏（1080×1920）导出、字幕/水印叠加等后期处理。
- 通过命令行入口一键跑通生成流水线。

## 快速开始
1. 复制 `.env.example` 为 `.env`，补充本地资源路径或密钥。
2. 根据需求修改 `configs/default.yaml`。
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 执行命令行：
   ```bash
   python -m src.runner.cli --count 1
   ```

> **提示**：项目主要用于构建自动化视频宣传/短视频生成工作流，实际模型推理部分需根据本地环境做进一步实现。
