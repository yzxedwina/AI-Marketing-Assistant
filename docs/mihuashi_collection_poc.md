# 米画师公开字段采集 PoC

## 目标与边界

该 PoC 默认使用米画师公开“画师列表”验证网页读取能力，仅采集最多 3 位画师的公开昵称和主页链接。也可传入公开主页 URL 验证主页字段。每次只打开一个页面、不并发、不自动重试，并在加载后随机等待 3—7 秒。随机等待用于降低请求压力，不用于伪装真人或规避平台检测。它不会登录、读取私信或订单、解决验证码、绕过访问控制，也不会把不可见字段补写为 0。

采集结果包含来源链接、采集时间、HTTP 状态、字段可用状态、公开计数和最多 1—5 条可见作品或橱窗链接。页面未公开的字段保存为 `null`，状态为 `not_visible`。

## 运行

```bash
source .venv/bin/activate
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers python scripts/collect_mihuashi_public.py --limit 3
```

需要观察页面时可加 `--headed`。结果写入 `data/collected/mihuashi/`。如果出现登录、验证码、安全验证或页面结构变化，脚本会留下失败记录并停止。

## 稳定性口径

“稳定”指：同一公开页面可重复运行、输出固定 JSON 结构、字段缺失不导致整批失败、最多采集少量记录，并保存来源与时间用于审计。它不代表平台页面、字段名称或访问策略永远不会变化；正式接入前仍需核对当前平台条款并定期维护选择器。

橱窗列表必须从 `/stalls` 页面内点击“全部橱窗”进入。脚本不会自行构造或逆向平台签名；若站内导航仍显示签名错误，则停止采集。

## 登录会话 PoC

匿名访问出现签名错误时，可由用户在独立 Chromium 中亲自登录备用账号一次。账号密码不进入代码；本地会话保存在 `data/browser_profiles/mihuashi/` 且被 Git 忽略。采集器只读取橱窗页公开展示字段，不进入私信、订单或客户资料。出现验证码、限流或账号警告时立即停止。
