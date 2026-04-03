# mopng-api

MoPNG API Skill for OpenClaw - 使用 mopng.cn API 进行图片处理。

## 功能

- **智能抠图** (`remove-bg`) - 自动去除图片背景
- **高清放大** (`upscale`) - 图片无损放大 2x/4x
- **智能扩图** (`outpainting`) - AI 智能扩展图片边界
- **图片翻译** (`translation`) - 翻译图片中的文字
- **文生图** (`text-to-image`) - 从文本描述生成图片
- **图生图** (`image-to-image`) - 基于参考图生成新图片

## 安装

1. 克隆仓库到 OpenClaw skills 目录
2. 确保已安装 Python 3.10+ 和 uv
3. 配置 `MOPNG_API_KEY` 环境变量

## 配置

在 OpenClaw 配置文件中设置 API Key：

```json
{
  "env": {
    "MOPNG_API_KEY": "ak_your_api_key_here"
  }
}
```

## Claude 命令使用示例

### 智能抠图

```
remove-bg ./photo.jpg
```

```
remove-bg ./photo.jpg --output ./result.png --async-mode
```

### 高清放大

```
upscale ./photo.jpg --scale 2
```

```
upscale ./photo.jpg --scale 4 --tile-size 192 --tile-pad 24 --async-mode
```

### 智能扩图

```
outpainting ./photo.jpg --direction all --expand-ratio 0.5
```

```
outpainting ./photo.jpg --direction right --expand-ratio 0.3 --best-quality
```

### 图片翻译

```
translation ./photo.jpg --target-language en
```

```
translation ./photo.jpg --target-language ja --source-language zh
```

### 文生图

```
text-to-image --prompt "一只红嘴蓝鹊站在树枝上"
```

```
text-to-image --prompt "赛博朋克风格的未来城市" --output ./cyberpunk.png --model wanx-v2.5
```

### 图生图

```
image-to-image --input ./photo.jpg --prompt "把天空变成日落金色"
```

```
image-to-image --input ./portrait.jpg --prompt "转换为油画风格" --strength 0.7 --output ./portrait_oil.png
```

### 查看可用模型

```
list-models --type text_to_image
```

```
list-models --type image_to_image
```

## 命令参数速查

| 命令 | 必填参数 | 常用可选参数 |
|------|----------|--------------|
| `remove-bg` | `--input` | `--output`, `--output-format`, `--async-mode` |
| `upscale` | `--input` | `--output`, `--scale`, `--tile-size`, `--tile-pad`, `--async-mode` |
| `outpainting` | `--input` | `--output`, `--direction`, `--expand-ratio`, `--best-quality` |
| `translation` | `--input`, `--target-language` | `--output`, `--source-language` |
| `text-to-image` | `--prompt` | `--output`, `--model`, `--width`, `--height`, `--negative-prompt` |
| `image-to-image` | `--input`, `--prompt` | `--output`, `--strength`, `--model`, `--negative-prompt` |

## 使用技巧

### 1. 简化路径输入

Claude 会自动处理路径，可以直接输入：
```
remove-bg photo.jpg
```

### 2. 异步模式

对于耗时操作（抠图、放大），建议使用 `--async-mode`：
```
upscale photo.jpg --scale 2 --async-mode
```

### 3. 指定输出路径

默认会保存到工作区目录，也可以指定完整路径：
```
text-to-image --prompt "小猫" --output ./images/kitten.png
```

### 4. 图生图强度控制

`--strength` 参数控制变化程度：
- 0.3-0.5: 轻微变化，保留原图特征
- 0.6-0.8: 中等变化，风格转换
- 0.9-1.0: 大幅变化，仅保留构图

## 测试

```bash
uv run python -m pytest tests/test_mopng_api.py -v
```

## API 文档

详见 [mopng.cn/agent/docs](https://mopng.cn/agent/docs)

## 许可证

MIT
