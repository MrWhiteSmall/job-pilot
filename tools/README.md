# tools/ 开发与运维脚本

主程序不需要这里的任何文件。这些是排查和运维用的，都按「相对项目根目录」定位数据，没有写死路径。

| 脚本 | 用途 |
| --- | --- |
| `watchdog.py` | 无人值守看门狗：45 秒探一次 `/api/state`，进程挂了自动重启；只在**瞬时故障**（worker 报错、采集失败）时重新开启托管，遇到平台级暂停（额度/登录/验证码）只记录、不擅自重开。用 `pythonw tools/watchdog.py` 后台跑。 |
| `audit_rejections.py` | 复盘被淘汰的岗位：用当前规则重算每条 `rejected`，按原因分组输出到 `data/audit-rejections.md`，用来发现误杀。改完规则想知道「到底筛掉了什么」时跑它。 |
| `analyze_backlog.py` | 循环调 `/api/analyze` 直到没有待分析岗位，结束后打印状态分布和拒绝原因 Top N。改规则后（会清空非终态分数）用它一次性补算。 |
| `check_pending.py` | 退出码 1 表示还有 `pending` 的真实尝试正在进行。**重启 app 前先跑它**，否则可能把一次发送打断成未知状态。 |
| `shot_dashboard.py` | 用 headless Chrome 截当前看板（桌面 1440 + 手机 390）到 `data/screenshots/`，改完样式用它确认布局。 |

约定：这些脚本读写的是 `data/job_pilot.sqlite3`（可用 `JOB_PILOT_DB` 覆盖），不会提交任何数据到仓库。
