window.GROWTH_DASHBOARD_DATA = {
  state: {
    title: "Investing-OS Growth Dashboard",
    subtitle: "主脑视角：认知核心 × 决策系统 × 执行系统 × 进化系统",
    permission: "Red",
    permissionCn: "红色权限",
    activeRisk: "MUU trapped leveraged position / MUU 杠杆仓位仍未完全处理",
    nextAction: "盘前重新决策：只允许风险处理、复盘、研究，不允许新短线交易",
    boundary: "所有入口从 investing-os 开始。stock_team 只提供被主脑调用后的事实证据包，不直接给出交易建议。"
  },
  systems: [
    { id: "cognition", label: "Cognition\n认知核心", x: 235, y: 130, files: ["self", "mistake", "emotion", "bias", "strength"] },
    { id: "decision", label: "Decision\n决策系统", x: 565, y: 130, files: ["portfolio", "risk", "tactic", "watch"] },
    { id: "execution", label: "Execution\n执行系统", x: 660, y: 360, files: ["pre", "intra", "post", "weekly"] },
    { id: "evolution", label: "Evolution\n进化系统", x: 400, y: 530, files: ["queue", "rules", "loop", "log"] },
    { id: "wiki", label: "Wiki\n长期记忆", x: 140, y: 360, files: ["journals", "sources", "companies", "cases"] },
    { id: "system", label: "System\n流程契约", x: 400, y: 95, files: ["checks", "trace", "packets", "workflow"] }
  ],
  files: {
    self: { label: "self-model.md", path: "cognition/self-model.md", x: 110, y: 80 },
    mistake: { label: "mistake-patterns.md", path: "cognition/mistake-patterns.md", x: 115, y: 150 },
    emotion: { label: "emotional-patterns.md", path: "cognition/emotional-patterns.md", x: 235, y: 55 },
    bias: { label: "bias-map.md", path: "cognition/bias-map.md", x: 255, y: 205 },
    strength: { label: "strengths.md", path: "cognition/strengths-and-weaknesses.md", x: 345, y: 125 },
    portfolio: { label: "portfolio-thesis.md", path: "decision/portfolio-thesis.md", x: 520, y: 55 },
    risk: { label: "risk-budget.md", path: "decision/risk-budget.md", x: 670, y: 75 },
    tactic: { label: "rs tactic", path: "decision/tactics/rs-pullback-rebound-candidate.md", x: 690, y: 165 },
    watch: { label: "watchlist.md", path: "decision/current-watchlist.md", x: 535, y: 220 },
    pre: { label: "pre-market.md", path: "execution/pre-market.md", x: 720, y: 300 },
    intra: { label: "intraday.md", path: "execution/intraday.md", x: 740, y: 380 },
    post: { label: "post-market.md", path: "execution/post-market.md", x: 650, y: 470 },
    weekly: { label: "weekly-use-cases.md", path: "execution/weekly-use-cases.md", x: 540, y: 430 },
    queue: { label: "promotion-queue.md", path: "evolution/promotion-queue.md", x: 280, y: 590 },
    rules: { label: "promotion-rules.md", path: "evolution/promotion-rules.md", x: 400, y: 630 },
    loop: { label: "learning-loop.md", path: "evolution/learning-loop.md", x: 525, y: 585 },
    log: { label: "system-update-log.md", path: "evolution/system-update-log.md", x: 410, y: 500 },
    journals: { label: "journals/", path: "wiki/journals/", x: 55, y: 300 },
    sources: { label: "sources/", path: "wiki/sources/", x: 55, y: 385 },
    companies: { label: "companies/", path: "wiki/companies/", x: 145, y: 470 },
    cases: { label: "historical-cases/", path: "wiki/historical-cases/", x: 245, y: 425 },
    checks: { label: "checks/", path: "system/checks/", x: 305, y: 48 },
    trace: { label: "traceability/", path: "system/traceability/", x: 405, y: 38 },
    packets: { label: "packets/", path: "system/data/packets/", x: 505, y: 48 },
    workflow: { label: "workflows/", path: "system/workflows/", x: 405, y: 145 }
  },
  lessons: [
    {
      id: "CAND-2026-06-06-001",
      title: "Profit Streak Overconfidence",
      cn: "连续盈利后的过度自信",
      status: "adopted",
      source: "wiki/journals/2026-06-05-major-drawdown-review.md",
      x: 90,
      y: 555,
      summary: "近期盈利、COHR 大赢家、顺风市场和短线小胜放大了手感自信。",
      targets: ["queue", "bias", "emotion", "mistake", "checks"]
    },
    {
      id: "CAND-2026-06-06-002",
      title: "No New Short-Term Trade After Stop",
      cn: "短线止损后停止新短线",
      status: "adopted",
      source: "wiki/journals/2026-06-05-major-drawdown-review.md",
      x: 735,
      y: 540,
      summary: "短线失败止损后，心态和手感已经被污染，当日只能处理风险或执行盘前预案。",
      targets: ["queue", "intra", "checks"]
    },
    {
      id: "CAND-2026-06-06-003",
      title: "Red Permission State",
      cn: "重大回撤后的红色权限",
      status: "adopted",
      source: "wiki/journals/2026-06-05-major-drawdown-review.md",
      x: 760,
      y: 90,
      summary: "本金受损、情绪崩溃、未处理高风险仓位出现后，系统进入红色权限。",
      targets: ["queue", "intra", "risk", "workflow"]
    },
    {
      id: "CAND-2026-06-06-004",
      title: "Thesis / Underlying / Instrument Split",
      cn: "主题、底层标的、交易工具分离",
      status: "adopted",
      source: "wiki/journals/2026-06-05-major-drawdown-review.md",
      x: 35,
      y: 95,
      summary: "AI/存储主线成立，不等于 MU 一定强；MU 强，也不等于 MUU 适合持有。",
      targets: ["bias", "risk", "portfolio"]
    },
    {
      id: "CAND-2026-06-06-005",
      title: "RS Pullback Rebound Tactic",
      cn: "RS 回撤反弹战术",
      status: "evidence_received_pending_review",
      source: "wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md",
      x: 400,
      y: 675,
      summary: "stock_team 回测已收到：整体有正期望，但 high-volume risk-off 为负，不能升级为无限制实盘规则。",
      targets: ["queue", "tactic", "sources", "trace"]
    }
  ],
  reports: [
    {
      id: "RPT-2026-06-05-MAJOR-DRAWDOWN",
      title: "2026-06-05 Major Drawdown Review",
      cn: "2026-06-05 最大单日回撤复盘",
      path: "wiki/journals/2026-06-05-major-drawdown-review.md",
      type: "post_market_review",
      status: "absorbed",
      lessons: [
        "CAND-2026-06-06-001",
        "CAND-2026-06-06-002",
        "CAND-2026-06-06-003",
        "CAND-2026-06-06-004",
        "CAND-2026-06-06-005"
      ],
      summary: "短线战术在 risk-off 环境失效，杠杆工具放大亏损，形成 MUU trapped position，并触发红色权限。"
    },
    {
      id: "SRC-2026-06-06-RS-BACKTEST",
      title: "Stock Team RS Pullback Backtest Evidence",
      cn: "stock_team RS 回撤反弹回测证据",
      path: "wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md",
      type: "evidence_source",
      status: "absorbed_pending_review",
      lessons: ["CAND-2026-06-06-005"],
      summary: "213 次交易、胜率 62.91%、PF 1.33；QQQ high-volume risk-off 为负期望。"
    }
  ],
  fileLineage: {
    "queue": [
      { lesson: "CAND-2026-06-06-001", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" },
      { lesson: "CAND-2026-06-06-002", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" },
      { lesson: "CAND-2026-06-06-003", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" },
      { lesson: "CAND-2026-06-06-005", report: "SRC-2026-06-06-RS-BACKTEST", status: "evidence_received_pending_review" }
    ],
    "bias": [
      { lesson: "CAND-2026-06-06-001", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" },
      { lesson: "CAND-2026-06-06-004", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" }
    ],
    "emotion": [
      { lesson: "CAND-2026-06-06-001", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" }
    ],
    "mistake": [
      { lesson: "CAND-2026-06-06-001", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" }
    ],
    "checks": [
      { lesson: "CAND-2026-06-06-001", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" },
      { lesson: "CAND-2026-06-06-002", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" }
    ],
    "intra": [
      { lesson: "CAND-2026-06-06-002", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" },
      { lesson: "CAND-2026-06-06-003", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" }
    ],
    "risk": [
      { lesson: "CAND-2026-06-06-003", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" },
      { lesson: "CAND-2026-06-06-004", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" }
    ],
    "tactic": [
      { lesson: "CAND-2026-06-06-005", report: "SRC-2026-06-06-RS-BACKTEST", status: "evidence_received_pending_review" }
    ],
    "sources": [
      { lesson: "CAND-2026-06-06-005", report: "SRC-2026-06-06-RS-BACKTEST", status: "evidence_received_pending_review" }
    ],
    "trace": [
      { lesson: "CAND-2026-06-06-005", report: "SRC-2026-06-06-RS-BACKTEST", status: "evidence_received_pending_review" }
    ],
    "portfolio": [
      { lesson: "CAND-2026-06-06-004", report: "RPT-2026-06-05-MAJOR-DRAWDOWN", status: "adopted" }
    ]
  },
  capabilities: [
    { id: "research", label: "Research", cn: "研究", score: 59, previous: 58, source: "major drawdown review", reason: "开始区分主题、底层标的和交易工具。" },
    { id: "risk", label: "Risk", cn: "风险", score: 68, previous: 66, source: "major drawdown review", reason: "识别杠杆路径风险、MAE、账户名义暴露和红色权限。" },
    { id: "discipline", label: "Discipline", cn: "纪律", score: 38, previous: 40, source: "major drawdown review", reason: "短线止损后继续 re-entry，纪律分下降。" },
    { id: "execution", label: "Execution", cn: "执行", score: 41, previous: 43, source: "major drawdown review", reason: "risk-off 环境里使用杠杆工具放大战术失败。" },
    { id: "emotion", label: "Emotion", cn: "情绪", score: 55, previous: 54, source: "major drawdown review", reason: "识别不甘心、修复冲动、得意忘形和 thesis attachment。" },
    { id: "review", label: "Review", cn: "复盘", score: 61, previous: 59, source: "major drawdown review", reason: "完成事件链、市场背景、经验落点和系统吸收。" }
  ],
  tasks: [
    { group: "Premarket / 盘前", text: "MUU 必须盘前重新决策，不能在情绪中盘中临时决定。" },
    { group: "Dashboard / 可视化", text: "文件节点现在可查看来源；下一步把静态索引生成脚本接入复盘流程。" },
    { group: "stock_team / 肌肉", text: "继续做 evidence exporter 和 repo 提纯，但入口仍由 investing-os 编排。" }
  ]
};
