window.GROWTH_DASHBOARD_INDEXES = {
  reports: [
  {
    "id": "RPT-2026-06-05-MAJOR-DRAWDOWN",
    "title": "2026-06-05 Major Drawdown Review",
    "cn": "2026-06-05 最大单日回撤复盘",
    "path": "wiki/journals/2026-06-05-major-drawdown-review.md",
    "html_path": "dashboards/reports/2026-06-05-major-drawdown-review.html",
    "type": "post_market_review",
    "status": "absorbed",
    "lessons": [
      "CAND-2026-06-06-001",
      "CAND-2026-06-06-002",
      "CAND-2026-06-06-003",
      "CAND-2026-06-06-004",
      "CAND-2026-06-06-005"
    ],
    "summary": "短线战术在 risk-off 环境失效，杠杆工具放大亏损，形成 MUU trapped position，并触发红色权限。"
  },
  {
    "id": "SRC-2026-06-06-RS-BACKTEST",
    "title": "Stock Team RS Pullback Backtest Evidence",
    "cn": "stock_team RS 回撤反弹回测证据",
    "path": "wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md",
    "type": "evidence_source",
    "status": "absorbed_pending_review",
    "lessons": [
      "CAND-2026-06-06-005"
    ],
    "summary": "213 次交易、胜率 62.91%、PF 1.33；QQQ high-volume risk-off 为负期望。"
  }
]
,
  lessons: [
  {
    "id": "CAND-2026-06-06-001",
    "title": "Profit Streak Overconfidence",
    "cn": "连续盈利后的过度自信",
    "status": "adopted",
    "source": "wiki/journals/2026-06-05-major-drawdown-review.md",
    "summary": "近期盈利、COHR 大赢家、顺风市场和短线小胜放大了手感自信。",
    "targets": ["queue", "bias", "emotion", "mistake", "checks"]
  },
  {
    "id": "CAND-2026-06-06-002",
    "title": "No New Short-Term Trade After Stop",
    "cn": "短线止损后停止新短线",
    "status": "adopted",
    "source": "wiki/journals/2026-06-05-major-drawdown-review.md",
    "summary": "短线失败止损后，心态和手感已经被污染，当日只能处理风险或执行盘前预案。",
    "targets": ["queue", "intra", "checks"]
  },
  {
    "id": "CAND-2026-06-06-003",
    "title": "Red Permission State",
    "cn": "重大回撤后的红色权限",
    "status": "adopted",
    "source": "wiki/journals/2026-06-05-major-drawdown-review.md",
    "summary": "本金受损、情绪崩溃、未处理高风险仓位出现后，系统进入红色权限。",
    "targets": ["queue", "intra", "risk", "workflow"]
  },
  {
    "id": "CAND-2026-06-06-004",
    "title": "Thesis / Underlying / Instrument Split",
    "cn": "主题、底层标的、交易工具分离",
    "status": "adopted",
    "source": "wiki/journals/2026-06-05-major-drawdown-review.md",
    "summary": "AI/存储主线成立，不等于 MU 一定强；MU 强，也不等于 MUU 适合持有。",
    "targets": ["bias", "risk", "portfolio"]
  },
  {
    "id": "CAND-2026-06-06-005",
    "title": "RS Pullback Rebound Tactic",
    "cn": "RS 回撤反弹战术",
    "status": "evidence_received_pending_review",
    "source": "wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md",
    "summary": "stock_team 回测已收到：整体有正期望，但 high-volume risk-off 为负，不能升级为无限制实盘规则。",
    "targets": ["queue", "tactic", "sources", "trace"]
  }
]
,
  fileLineage: {
  "queue": [
    { "lesson": "CAND-2026-06-06-001", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" },
    { "lesson": "CAND-2026-06-06-002", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" },
    { "lesson": "CAND-2026-06-06-003", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" },
    { "lesson": "CAND-2026-06-06-005", "report": "SRC-2026-06-06-RS-BACKTEST", "status": "evidence_received_pending_review" }
  ],
  "bias": [
    { "lesson": "CAND-2026-06-06-001", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" },
    { "lesson": "CAND-2026-06-06-004", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" }
  ],
  "emotion": [
    { "lesson": "CAND-2026-06-06-001", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" }
  ],
  "mistake": [
    { "lesson": "CAND-2026-06-06-001", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" }
  ],
  "checks": [
    { "lesson": "CAND-2026-06-06-001", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" },
    { "lesson": "CAND-2026-06-06-002", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" }
  ],
  "intra": [
    { "lesson": "CAND-2026-06-06-002", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" },
    { "lesson": "CAND-2026-06-06-003", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" }
  ],
  "risk": [
    { "lesson": "CAND-2026-06-06-003", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" },
    { "lesson": "CAND-2026-06-06-004", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" }
  ],
  "tactic": [
    { "lesson": "CAND-2026-06-06-005", "report": "SRC-2026-06-06-RS-BACKTEST", "status": "evidence_received_pending_review" }
  ],
  "sources": [
    { "lesson": "CAND-2026-06-06-005", "report": "SRC-2026-06-06-RS-BACKTEST", "status": "evidence_received_pending_review" }
  ],
  "trace": [
    { "lesson": "CAND-2026-06-06-005", "report": "SRC-2026-06-06-RS-BACKTEST", "status": "evidence_received_pending_review" }
  ],
  "portfolio": [
    { "lesson": "CAND-2026-06-06-004", "report": "RPT-2026-06-05-MAJOR-DRAWDOWN", "status": "adopted" }
  ]
}
,
  capabilityHistory: [
  { "date": "2026-06-06", "dimension": "Research", "previous": 58, "current": 59, "delta": 1, "source": "wiki/journals/2026-06-05-major-drawdown-review.md", "reason": "开始区分主题、底层标的和交易工具。" },
  { "date": "2026-06-06", "dimension": "Risk", "previous": 66, "current": 68, "delta": 2, "source": "wiki/journals/2026-06-05-major-drawdown-review.md", "reason": "识别杠杆路径风险、MAE、账户名义暴露和红色权限。" },
  { "date": "2026-06-06", "dimension": "Discipline", "previous": 40, "current": 38, "delta": -2, "source": "wiki/journals/2026-06-05-major-drawdown-review.md", "reason": "短线止损后继续 re-entry，纪律分下降。" },
  { "date": "2026-06-06", "dimension": "Execution", "previous": 43, "current": 41, "delta": -2, "source": "wiki/journals/2026-06-05-major-drawdown-review.md", "reason": "risk-off 环境里使用杠杆工具放大战术失败。" },
  { "date": "2026-06-06", "dimension": "Emotion", "previous": 54, "current": 55, "delta": 1, "source": "wiki/journals/2026-06-05-major-drawdown-review.md", "reason": "识别不甘心、修复冲动、得意忘形和 thesis attachment。" },
  { "date": "2026-06-06", "dimension": "Review", "previous": 59, "current": 61, "delta": 2, "source": "wiki/journals/2026-06-05-major-drawdown-review.md", "reason": "完成事件链、市场背景、经验落点和系统吸收。" }
]

};
