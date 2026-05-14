# TODO — ryn_stock_team

## 已完成 (9/15)
- [x] **项目基底替换** — stock_team 为模板，整合 ryn 增长点
- [x] **SentimentAgent → VADER NLP** — 替换关键词计数
- [x] **CommunityAgent → +Xueqiu 雪球** — 中文情绪分析
- [x] **47个技术指标注入 DataAgent** — `indicators/compute_indicators.py`
- [x] **安全过滤器 (F1-F8)** — 三级警告模式，注入 CIO Phase 3
- [x] **日志框架** — `utils/log_config.py`，文件+控制台双输出，13个关键模块已集成
- [x] **yfinance 重试+退避** — `utils/retry.py`，3次重试+指数退避，覆盖所有网络调用
- [x] **Reddit OAuth** — praw 优先，raw search 回退，速率限制处理
- [x] **原子文件写入** — `utils/atomic.py`，write-tmp+os.replace，全部 json.dump 已替换

## 待办

### 核心增强
- [ ] **策略吸取量化交易精髓** — 排除不适合A股/散户的部分，保留仓位管理、风控、信号过滤

### 模拟盘
- [ ] **模拟盘优化** — 提升回测精度、增加多账户对比、优化演化报告

### 可视化
- [ ] **全流程可视化操作界面** — 网页/GUI，展示Phase 0→3流程、各Agent信号、辩论过程、仪表盘

### 独立工具（暂缓）
- [ ] **终端仪表盘** — 读取 paper_trading/ 和 discussion_board.jsonl 展示
- [ ] **回测框架** — 基于 paper_trader 的历史回放 + 参数网格搜索
- [ ] **数据库持久化层** — 21表+3视图，可选启用

### 数据源扩展
- [ ] **小红书情绪数据源** — 爬取/API获取中文散户情绪，整合进 CommunityAgent
- [ ] **盘中轮询性能测试** — 2分钟密度能否支撑，实盘网络条件验证
