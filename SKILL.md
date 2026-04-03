---
name: mopng-api
description: 使用 mopng.cn (MoPNG) API 进行图片处理，包括智能抠图、高清放大、智能扩图、图片翻译、文生图、图生图等功能。支持 API Key 鉴权。
metadata:
  {
    "openclaw": {
      "requires": { "bins": ["uv", "python3"], "env": ["MOPNG_API_KEY"] },
      "primaryEnv": "MOPNG_API_KEY"
    }
  }
---

# mopng-api

使用 mopng.cn (MoPNG) 的 OpenAPI 进行多种图片处理任务。

## API key setup

1. 登录 [mopng.cn/agent](https://mopng.cn/agent) 获取 API Key
2. **OpenClaw**：在 `openclaw.json` 的 `env` 中设置 `MOPNG_API_KEY`
3. **Claude Code**：
   - 执行 `/skill add https://github.com/jkin8010/mopng-api/blob/main/SKILL.md`
   - 按上一步在控制台创建并复制 API Key
   - 在对话中输入：`在全局环境中 MOPNG_API_KEY='你的密钥'`（引号内换成真实 Key；勿写入仓库或提交 Git）
   - 测试文生图：在对话中输入 `text-to-image --prompt '一只猫咪' --output ./cat.jpg`

更完整的说明见仓库根目录 `README.md` 的「Claude Code」小节。

## 功能列表

| 功能 | 命令 | 计费 |
|------|------|------|
| 智能抠图 | `remove-bg` | 1点/张 |
| 高清放大 | `upscale` | 2点/张 |
| 智能扩图 | `outpainting` | 按量计费 |
| 图片翻译 | `translation` | 按量计费 |
| 文生图 | `text-to-image` | 按量计费 |
| 图生图 | `image-to-image` | 按量计费 |

## 使用方法

### 智能抠图 (remove-bg)

```bash
uv run scripts/mopng_api.py remove-bg --input ./photo.jpg --output ./result.png
```

选项：
- `--output-format png|jpg` (默认: png)
- `--return-mask` 返回蒙版
- `--only-mask` 仅返回蒙版
- `--async-mode` 异步模式（需轮询）

### 高清放大 (upscale)

```bash
uv run scripts/mopng_api.py upscale --input ./photo.jpg --output ./result.png --scale 2
```

选项：
- `--scale 2|4` 放大倍数 (默认: 2)
- `--tile-size` 瓦片大小 (默认: 0)
- `--tile-pad` 瓦片填充 (默认: 10)
- `--output-format png|jpg`
- `--async-mode`

### 智能扩图 (outpainting)

```bash
uv run scripts/mopng_api.py outpainting --input ./photo.jpg --output ./result.png --direction all --expand-ratio 0.5
```

选项：
- `--direction all|up|down|left|right` 扩展方向 (默认: all)
- `--expand-ratio` 扩展比例 0.1-1.0 (默认: 0.5)
- `--angle` 旋转角度 (默认: 0)
- `--best-quality` 最佳质量

### 图片翻译 (translation)

```bash
uv run scripts/mopng_api.py translation --input ./photo.jpg --output ./result.png --target-language en
```

选项：
- `--source-language` 源语言 (默认: auto)
- `--target-language` 目标语言，如 en, zh, ja, ko 等 (必填)
- `--domain-hint` 领域提示
- `--sensitive-word-filter` 敏感词过滤

### 文生图 (text-to-image)

```bash
uv run scripts/mopng_api.py text-to-image --prompt "一只红嘴蓝鹊站在树枝上" --output ./result.png --model wanx-v2.5
```

选项：
- `--prompt` 提示词 (必填)
- `--model` 模型名称 (默认: wanx-v2.5)
- `--negative-prompt` 负面提示词
- `--width/--height` 图片尺寸
- `--n` 生成数量

### 图生图 (image-to-image)

```bash
uv run scripts/mopng_api.py image-to-image --input ./photo.jpg --prompt "把天空变成日落金色" --output ./result.png --model wanx-v2.5
```

选项：
- `--prompt` 编辑提示词 (必填)
- `--model` 模型名称 (默认: wanx-v2.5)
- `--negative-prompt` 负面提示词
- `--strength` 编辑强度

## 安全约束

- `--input` 必须是 OpenClaw 工作区内的真实图片文件
- 允许的输入格式: `.png`, `.jpg`, `.jpeg`, `.webp`
- `--output` 最终必须位于 `outputs/mopng-api/` 下；写法为相对路径（如 `./cat.jpg`）时会自动落到该目录
- 大文件会被拒绝（大小和尺寸限制）

## 异步任务

当使用 `--async-mode` 时，首次响应可能状态为 pending/processing。脚本会自动轮询直到任务完成。

轮询间隔：2-5 秒

## 输出

- 结果文件写入 `--output` 指定路径
- 打印 `MEDIA:` 行用于聊天工作流

## 模型发现

文生图/图生图前，可以先查询可用模型：

```bash
uv run scripts/mopng_api.py list-models --type text_to_image
```

## 注意事项

- API 调用会消耗账户积分
- 本地图片会自动上传到临时存储获取 URL
- 远程 URL 可直接使用，无需上传
