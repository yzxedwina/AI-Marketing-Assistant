# GitHub 上线说明

## 上线结构

- GitHub 保存代码并触发部署。
- Render 使用 Docker 同时运行网页、FastAPI、AI 接口和 Playwright。
- SQLite 写入 Render 持久磁盘，保存五个账号各自的画像、偏好、对话分析和复盘记录。
- 浏览器本地缓存也按账号编号分区，但服务器 Memory 才是跨设备长期记录。

## 必须在托管平台手动填写的秘密

- DEEPSEEK_API_KEY：DeepSeek API Key。
- PRESEEDED_ACCOUNTS_JSON：data/private/preseed_accounts.json 的完整内容。

这两个值不得写入 GitHub。五个账号的分发清单只保存在
data/private/friend_accounts.csv。

## 首次部署

1. 在 GitHub 新建私有仓库并推送本项目。
2. 在 Render 中选择 New Blueprint 并连接该仓库。
3. Render 读取根目录的 render.yaml。
4. 按提示填写两个秘密环境变量。
5. 完成部署后，用五个账号分别登录并建立画像。

## 已知边界

- 持久磁盘是保存 Memory 的必要条件，因此该配置使用支持磁盘的付费 Web Service。
- 画加和小红书的公开页面可能触发登录、安全验证或页面结构变化。更新任务会在受限时停止并保留旧数据，不能承诺每次都取得 20 条。
- 五个账号共享同一份公共市场快照，但画像、偏好、分析历史和复盘结果按账号隔离。
- 当前为小规模 Demo，不支持自行注册、找回密码、修改密码和管理员后台。
