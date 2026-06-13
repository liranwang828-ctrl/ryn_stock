# Stock Intuition Learning System

自我提升选股系统 — 从市场结果和用户交易中持续学习

## 文件说明

| 文件 | 用途 |
|------|------|
| `historical_features.parquet` | 2年历史特征矩阵（bootstrap 生成） |
| `daily_harvest.jsonl` | 每日新增数据（结果+空头比例） |
| `short_interest_history.jsonl` | 空头比例时间序列 |
| `case_library.json` | 典型成功/失败案例库 |
| `model_intraday.pkl` | 日内胜率模型（RandomForest） |
| `model_swing.pkl` | 波段胜率模型（RandomForest） |
| `weights_log.json` | 模型更新历史 |

## 每日操作流程

### 盘前（08:00-09:15 ET）
```bash
# 扫描今日候选池
python3.12 agents/candidate_scanner.py --top 10

# 对候选标的做盘前分析（含直觉评分）
python3.12 agents/premarket.py [候选标的...]
```

### 盘中
```bash
# 2分钟轮询监控（已集成直觉评分）
python3.12 agents/poll.py [标的...]
```

### 收盘后（16:30 ET）
```bash
# 记录今日结果 + 空头比例
python3.12 agents/harvest_agent.py
```

### 每周五收盘后
```bash
# 重新训练模型 + 更新案例库
python3.12 agents/learning_agent.py
```

## 冷启动时间线

| 阶段 | 时间 | 有效特征 |
|------|------|---------|
| Day 1 | Bootstrap 完成 | 技术面全部 |
| Week 2 | 10+ 空头数据点 | +空头趋势 |
| Month 1 | 30+ 空头数据点 | +空头统计 |
| Month 2+ | 60+ 全量特征 | 全功率 |

## 成功标准

- 3个月后：主动推送标的 >50% 进用户当日观察列表
- 6个月后：波段胜率评分与实际5日收益相关性 >0.3
