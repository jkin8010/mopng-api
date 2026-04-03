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

按顺序完成以下步骤（将密钥中的 `xxxxxxxxxxxx` 替换为你在控制台复制的真实 API Key）：

1. 在 Claude Code 中输入：

   ```text
   /skill add https://github.com/jkin8010/mopng-api/blob/main/SKILL.md
   ```

2. 打开 [mopng.cn/agent](https://mopng.cn/agent)，登录并创建 API Key，复制密钥。

3. 在 Claude Code 中输入（把引号里的内容换成你复制的 API Key）：

   ```text
   在全局环境中 MOPNG_API_KEY='xxxxxxxxxxxx'
   ```

4. **测试文生图**：在 Claude Code 中输入：

   ```text
   text-to-image --prompt '一只猫咪' --output ./cat.jpg
   ```

**前置说明**：执行 skill 内的脚本仍需本机安装 Python 3.10+ 与 [uv](https://github.com/astral-sh/uv)。**不要将 API Key 写入仓库文件或提交到 Git。**

如需手动配置（不通过对话），也可在项目或用户级 `.claude/settings.local.json` 的 `env` 中设置 `MOPNG_API_KEY`。

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

## 使用

在 **Claude Code** 里完成安装并配置 `MOPNG_API_KEY` 后，用自然语言描述需求（例如「把这张 PNG 抠图并保存到 outputs」）即可；Agent 会按 `SKILL.md` 中的约定拼接 `uv run ... mopng_api.py` 命令。若在终端手动执行下方示例，请在 skill 所在目录下运行，或使用 Agent 给出的脚本完整路径。

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
