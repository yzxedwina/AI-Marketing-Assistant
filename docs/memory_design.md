# 简化长期 Memory（I 阶段）

## 目标

让同一用户第二次进入时，系统可读取其已确认画像、稳定偏好、历史 AI 结果和经营反馈。第一版使用本地 SQLite，强调可追溯和确定性，不需要 Embedding。

## 四类记忆

| 类型 | 写入条件 | 更新方式 | 示例 |
|---|---|---|---|
| 已确认画像 | `profile_status=confirmed` | 同一用户覆盖为最新确认版 | 经营目标、能力、价格、产能、禁区 |
| 已确认偏好 | 用户明确确认或编辑 | 按偏好键更新 | 传统手绘、宠物/兽设、水彩/平涂 |
| AI 分析历史 | Structured Output 已通过校验 | 按结果 ID 保存快照 | 机会方向、评分解释、营销方案 |
| 经营结果历史 | 用户回填或授权平台事实 | 只追加，不覆盖旧记录 | 曝光、收藏、咨询、成交、产能状态 |

## 不进入稳定 Memory

- 未经用户确认的 AI 候选判断。
- 临时热点、过期市场信号或模型自由发挥。
- 登录信息、Cookie、私聊原文、客户身份与订单隐私。
- 无数据来源的预测数字。

## 使用方式

首次初始化：

```bash
source .venv/bin/activate
python scripts/initialize_memory.py
```

启动 API 后，返回用户的页面先调用：

```text
GET /memory/USR-EDWINA-001
```

若 `has_memory=true`，前端用 `confirmed_profile` 和 `confirmed_preferences` 预填页面，并展示最近的 `analysis_history` 与 `outcome_history`。用户修改稳定信息后重新确认，再调用画像或偏好写入接口。

## 接口

- `GET /memory/{user_id}`：读取完整长期上下文。
- `PUT /memory/{user_id}/profile`：写入已确认画像；未确认画像会被拒绝。
- `PUT /memory/{user_id}/preferences`：写入一项明确确认的偏好。
- `POST /memory/{user_id}/analyses`：保存 AI 结构化结果快照。
- `POST /memory/{user_id}/outcomes`：追加一次经营反馈。

## 第二次进入判定

自动化测试会创建数据库、完成首次写入、关闭并重新创建 `MemoryStore`，再验证画像、偏好和历史结果仍可读取。这证明记忆不只存在于当前进程内。
