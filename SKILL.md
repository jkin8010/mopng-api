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

使用 mopng.cn 的 OpenAPI 进行多种图片处理任务。

## API Key 配置

1. 登录 https://mopng.cn/agent 获取 API Key
2. 在 OpenClaw 配置中设置 `MOPNG_API_KEY`

## 功能列表

| 功能 | 命令 | 计费 |
|------|------|------|
| 智能抠图 | `remove-bg` | 1点/张 |
| 高清放大 | `upscale` | 2点/张 |
| 智能扩图 | `outpainting` | 按量计费 |
| 图片翻译 | `translation` | 按量计费 |
| 文生图 | `text-to-image` | 按量计费 |
| 图生图 | `image-to-image` | 按量计费 |

## Claude 命令使用指南

### 智能抠图 (remove-bg)


**基本用法：**
```
remove-bg ./photo.jpg
```

**指定输出路径：**
```
remove-bg ./photo.jpg --output ./result.png
```

**选项说明：**
- `--output ./result.png` 指定输出路径
- `--output-format png|jpg` 输出格式（默认: png）
- `--return-mask` 返回蒙版
- `--only-mask` 仅返回蒙版
- `--async-mode` 异步模式（大文件建议使用）

---

### 高清放大 (upscale)

**基本用法（2倍放大）：**
```
upscale ./photo.jpg
```

**指定放大倍数：**
```
upscale ./photo.jpg --scale 4 --output ./result.png
```

**选项说明：**
- `--scale 2|4` 放大倍数（默认: 2）
- `--tile-size 192` 瓦片大小（默认: 0）
- `--tile-pad 24` 瓦片填充（默认: 10）
- `--output-format png|jpg` 输出格式
- `--async-mode` 异步模式（建议使用）

---

### 智能扩图 (outpainting)

**基本用法：**
```
outpainting ./photo.jpg
```

**指定扩展方向：**
```
outpainting ./photo.jpg --direction all --expand-ratio 0.5 --output ./result.png
```

**选项说明：**
- `--direction all|up|down|left|right` 扩展方向（默认: all）
- `--expand-ratio 0.1-1.0` 扩展比例（默认: 0.5）
- `--angle 0` 旋转角度
- `--best-quality` 最佳质量

---

### 图片翻译 (translation)

**基本用法：**
```
translation ./photo.jpg --target-language en
```

**选项说明：**
- `--target-language` 目标语言（必填），如 en, zh, ja, ko
- `--source-language` 源语言（默认: auto）
- `--domain-hint` 领域提示
- `--sensitive-word-filter` 敏感词过滤

---

### 文生图 (text-to-image)

**基本用法：**
```
text-to-image --prompt "一只红嘴蓝鹊站在树枝上"
```

**指定输出路径：**
```
text-to-image --prompt "一只可爱的猫咪" --output ./cat.png
```

**选项说明：**
- `--prompt "描述"` 提示词（必填）
- `--model wanx-v2.5` 模型名称（默认: wanx-v2.5）
- `--negative-prompt "描述"` 负面提示词
- `--width 1024 --height 1024` 图片尺寸
- `--n 1` 生成数量

---

### 图生图 (image-to-image)

**基本用法：**
```
image-to-image --input ./photo.jpg --prompt "把天空变成日落金色"
```

**选项说明：**
- `--input ./photo.jpg` 输入图片路径（必填）
- `--prompt "描述"` 编辑提示词（必填）
- `--model wanx-v2.5` 模型名称（默认: wanx-v2.5）
- `--negative-prompt "描述"` 负面提示词
- `--strength 0.7` 编辑强度（0.0-1.0，越大变化越大）
- `--width/--height` 输出尺寸

---

### 查看可用模型

```
list-models --type text_to_image
```

---

## 安全约束

- `--input` 必须是工作区内的真实图片文件
- 允许的输入格式: `.png`, `.jpg`, `.jpeg`, `.webp`
- `--output` 建议位于工作区目录下
- 大文件会被拒绝（大小和尺寸限制）

## 异步任务

当任务需要较长时间处理时，会自动进入异步模式。系统会轮询直到任务完成。

**轮询间隔：** 2-5 秒

## 注意事项

- API 调用会消耗账户积分
- 本地图片会自动上传到临时存储获取 URL
- 远程 URL 可直接使用，无需上传
