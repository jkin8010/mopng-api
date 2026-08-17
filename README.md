# mopng-api

面向 OpenClaw 的 MoPNG Agent Skill。它调用 qise-studio `motu-agent` 的公共 OpenAPI，让 UserAgent 与 MoPNG Agent 协商图片生成或修图方案，再由服务端执行功能链。

## 配置

```bash
export MOPNG_API_KEY='ak_...'                 # 私密配置，不要提交或粘贴到对话
export MOPNG_AGENT_BASE_URL='https://agent-api.mopng.cn'
```

`MOPNG_AGENT_BASE_URL` 默认是 `https://agent-api.mopng.cn`。客户端会自动请求 `/api/v1/open/agent`，鉴权头为 `X-API-Key`。

查询服务端当前模型目录：

```bash
python3 scripts/mopng_agent.py models --capability text-to-image
```

## 一键协商

已有图片必须先有 `motu-agent` 可访问的 HTTPS URL；多个参考图可重复传入 `--reference-url`：

```bash
python3 scripts/mopng_agent.py run \
  --intent '把产品图背景换成白色，做电商主图' \
  --goal '背景替换' \
  --reference-url 'https://example.com/product.png' \
  --usage '电商主图' \
  --style-constraint '纯白背景，产品边缘干净' \
  --width 1024 --height 1024 --watch
```

纯文生图不传 `--reference-url`：

```bash
python3 scripts/mopng_agent.py run \
  --intent '生成一张电影感的橘猫宇航员海报' \
  --goal '文生图' --usage '海报' --watch
```

低于 `MOPNG_AGENT_AUTO_APPROVE_COST_POINTS`（默认 5 点）的方案会自动批准；其他方案停在 Plan 阶段，需显式执行 `approve`。

## 手动协商

```bash
python3 scripts/mopng_agent.py brief --intent '...' --goal '风格转换' --reference-url 'https://...'
python3 scripts/mopng_agent.py plan SESSION_ID
python3 scripts/mopng_agent.py revision SESSION_ID --plan-id PLAN_ID --round 2 \
  --feedback-json '[{"step":1,"type":"set_cost_mode","value":"premium"}]'
python3 scripts/mopng_agent.py approve SESSION_ID
python3 scripts/mopng_agent.py status SESSION_ID --watch
```

支持的 OpenAPI 操作是创建会话、读取 Plan、修订、批准、轮询执行、打断和删除会话。完整行为和安全边界见 [SKILL.md](SKILL.md)。

## 校验

```bash
uv run pytest tests/ -v
uv run bandit -r scripts -ll
```
