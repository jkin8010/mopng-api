# mopng-api

MoPNG API Skill for OpenClaw - 使用 mopng.cn (其色模图) API 进行图片处理。

## 功能

- **智能抠图** (`remove-bg`) - 自动去除图片背景
- **高清放大** (`upscale`) - 图片无损放大 2x/4x
- **智能扩图** (`outpainting`) - AI 智能扩展图片边界
- **图片翻译** (`translation`) - 翻译图片中的文字
- **文生图** (`text-to-image`) - 从文本描述生成图片
- **图生图** (`image-to-image`) - 基于参考图生成新图片

## 安装

### OpenClaw

1. 克隆本仓库到 OpenClaw 的 skills 目录
2. 确保已安装 Python 3.10+ 和 [uv](https://github.com/astral-sh/uv)
3. 配置 `MOPNG_API_KEY` 环境变量（见下方「配置」）

### Claude Code

Claude Code 通过 **Skill 目录**（内含本仓库根目录的 `SKILL.md`、`scripts/`、`pyproject.toml` 等）加载能力。

1. **前置条件**：本机已安装 Python 3.10+ 与 `uv`，并能在终端执行 `uv run`。

2. **安装到用户级（所有项目可用）**  
   将仓库放到 Claude Code 的用户 skills 目录，目录名建议与 skill 名一致：

   ```bash
   git clone <本仓库 URL> ~/.claude/skills/mopng-api
   ```

3. **安装到项目级（仅当前仓库）**  
   在项目根目录下创建 `.claude/skills/`，再克隆或复制 skill：

   ```bash
   mkdir -p .claude/skills
   git clone <本仓库 URL> .claude/skills/mopng-api
   ```

4. **刷新与识别**  
   重启 Claude Code 会话或重新打开项目后，Agent 会根据 `SKILL.md` 正文的描述在需要时加载该 skill。你也可以在对话中直接说明「使用 mopng-api / MoPNG 图片 API 处理某张图」以触发相关说明与命令。

5. **运行脚本时的路径**  
   - 用户级：先进入 skill 目录再执行，例如  
     `cd ~/.claude/skills/mopng-api && uv run scripts/mopng_api.py ...`  
   - 项目级：在**项目根目录**下可使用相对路径，例如  
     `uv run .claude/skills/mopng-api/scripts/mopng_api.py ...`

## 配置

### OpenClaw

在 OpenClaw 配置文件中设置 API Key：

```json
{
  "env": {
    "MOPNG_API_KEY": "ak_your_api_key_here"
  }
}
```

### Claude Code

在项目目录创建或编辑 `.claude/settings.local.json`（勿提交密钥；该文件通常已加入 `.gitignore`），写入：

```json
{
  "env": {
    "MOPNG_API_KEY": "ak_your_api_key_here"
  }
}
```

亦可把 `MOPNG_API_KEY` 写入本机 shell 配置文件（如 `~/.zshrc`），使 Claude Code 继承终端环境。**不要将 API Key 写入 `SKILL.md` 或提交到 Git。**

## 使用

在 **Claude Code** 里加载本 skill 后，用自然语言描述需求（例如「把这张 PNG 抠图并保存到 outputs」）即可；Agent 会按 `SKILL.md` 中的约定拼接 `uv run ... mopng_api.py` 命令。若在终端手动执行下方示例，请与上文「Claude Code → 运行脚本时的路径」保持一致。

### 智能抠图

```bash
uv run scripts/mopng_api.py remove-bg -i ./photo.jpg -o ./result.png
```

### 高清放大

```bash
uv run scripts/mopng_api.py upscale -i ./photo.jpg -o ./result.png --scale 2
```

### 智能扩图

```bash
uv run scripts/mopng_api.py outpainting -i ./photo.jpg -o ./result.png --direction all --expand-ratio 0.5
```

### 图片翻译

```bash
uv run scripts/mopng_api.py translation -i ./photo.jpg -o ./result.png --target-language en
```

### 文生图

```bash
uv run scripts/mopng_api.py text-to-image -p "一只红嘴蓝鹊站在树枝上" -o ./result.png --model wanx-v2.5
```

### 图生图

```bash
uv run scripts/mopng_api.py image-to-image -i ./photo.jpg -p "把天空变成日落金色" -o ./result.png
```

### 查看可用模型

```bash
uv run scripts/mopng_api.py list-models --type text_to_image
```

## 测试

```bash
uv run python -m pytest tests/test_mopng_api.py -v
```

## API 文档

详见 [mopng.cn/agent](https://mopng.cn/agent)

## 许可证

MIT
