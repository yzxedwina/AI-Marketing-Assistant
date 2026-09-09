# AI 输入输出设计（V1.0）

> 当前为 Demo 本地设计与校验阶段，不调用真实模型、不写入 API Key。对应规则版本 `business-rules-v1.0.0`，AI 契约版本 `1.0.0`。

## 设计结论

后端先完成画像确认、禁区排除、热点与 Opportunity Score 计算，再把单个候选的锁定事实、规则轨迹和证据白名单组成 Evidence Package。AI 只解释证据或生成文字草稿，不决定事实与分数。

数字防编造采用三层控制：

1. **字段隔离**：AI 输出没有分数、价格、销量、互动量和日期字段。
2. **证据白名单**：只能引用 `allowed_evidence_ids`，输出后逐项校验。
3. **数字拦截**：生成文案出现阿拉伯数字或全角数字就拒绝；界面数字只从后端 `locked_facts` 渲染。

Structured Outputs 保证结构，业务 Validator 保证候选一致、引用合法和事实边界。仅有 JSON Schema 不能证明内容真实。

## 两个 AI 任务

| 任务 | 输入 | 允许输出 | 禁止输出 |
|---|---|---|---|
| 机会解释 | 单候选 Evidence Package | 摘要、支持理由、反向因素、缺失信息、下一步 | 新分数、新事实、效果承诺、重排候选 |
| 营销文字方案 | 已确认方向、画像和允许证据 | 账号策略、标题、正文、构图、图片顺序、视频文字脚本 | 图片/视频、自动发布、虚构数字、成交承诺 |

## 在线链路

`评分结果 → 选择候选 → Evidence Package → Prompt + strict JSON Schema → 模型输出 → Pydantic 校验 → 证据白名单校验 → 数字校验 → 合并 locked_facts → 展示`

校验失败不得展示原始输出。Demo 返回 `validation_failed` 并允许重试；连续失败时降级为规则事实卡片。

## Evidence Package 必填字段

- `contract_version`、`task`、`profile_id`、`candidate_id`、`input_status`；
- `locked_facts`：规则版本、机会分、等级、置信度、分项分、证据时间；
- `rule_trace`：正向因素、反向因素、缺失信息；
- `allowed_evidence_ids` 与 `evidence`；
- 禁止数字文案、效果承诺和外部动作的约束。

## 固定输出状态

- `ready`：证据足够，必须至少引用一条合法证据。
- `insufficient_evidence`：关键证据不足，不得用常识补齐。
- `conflict`：证据冲突且现有规则无法消解。
- `blocked`：画像、权限或输入状态不满足前置条件。

所有输出对象使用 `additionalProperties: false`；字段缺失或多出字段均失败。

## 文件与验收

- `config/prompts/`：两套系统 Prompt。
- `config/schemas/`：两套 strict JSON Schema。
- `backend/ai_contracts.py`：证据包、结构/引用/数字校验、安全合并。
- `scripts/build_ai_request.py`：生成请求预览，不调用模型。
- `tests/test_ai_contracts.py`：篡改候选、非法引用、未知字段、数字文案等测试。

验收要求：合法输出通过；新增字段、篡改候选、白名单外引用、ready 无引用、文案含数字必须失败；模型输出永远不能覆盖 `locked_facts`。

## 当前取舍与后续

数字文案全禁是 Demo 的强护栏。后续若正文必须出现价格等事实，使用后端占位符（如 `{price_range}`）在模型输出通过后替换，仍不让模型直接生成数字。真实模型接入前，还需建立 Prompt 回归集和 Bad Case 集，再冻结模型版本及参数。
