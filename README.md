# mopng-api

MoPNG API Skill for OpenClaw - 使用 qise.cc (其色模图) API 进行图片处理。

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

## 使用

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

详见 [qise.cc/agent](https://qise.cc/agent)

## 许可证

MIT
