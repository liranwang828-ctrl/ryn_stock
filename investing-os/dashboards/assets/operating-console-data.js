window.OPERATING_CONSOLE_DATA = {
  updatedAt: "2026-06-14",
  title: "Investing-OS Operating Console",
  subtitle: "主入口：盘前、盘中、盘后、研究和系统认知都从这里进入。",
  permission: {
    state: "Red",
    labelZh: "红色权限",
    labelEn: "Red Permission",
    summary: "当前偏向复盘、研究和证据整理，避免无计划短线和过度风险。",
    allowed: [
      "复盘与情绪降温",
      "风险降低计划",
      "公司 / 行业研究",
      "盘前计划与证据收集"
    ],
    blocked: [
      "无计划短线",
      "杠杆产品扩张风险",
      "止损后立刻再交易",
      "为弥补亏损而加仓"
    ]
  },
  nextActions: [
    {
      id: "NA-001",
      priority: "High",
      title: "盘前重新决策 MUU",
      detail: "确认 thesis 是否仍有效，instrument 是否适合，trapped position 如何降风险。",
      route: "pre_market",
      evidenceNeeded: ["QQQ / VIX / MUU / MU 盘前与日线证据", "当前持仓与最大可承受亏损"]
    },
    {
      id: "NA-002",
      priority: "High",
      title: "等待 stock_team CLI contract 验收",
      detail: "主脑稳定调用证据引擎后，才能批量生成 packets。",
      route: "stock_team_contract",
      evidenceNeeded: ["CLI --help", "packet examples", "forbidden behavior check"]
    },
    {
      id: "NA-003",
      priority: "Medium",
      title: "继续 COHR / ORCL 长期研究",
      detail: "用完整研究流程沉淀 thesis、falsification 和 position role。",
      route: "company_research",
      evidenceNeeded: ["COHR peer packet", "ORCL company packet"]
    }
  ],
  routes: [
    {
      id: "pre_market",
      nameZh: "盘前计划",
      nameEn: "Pre-market Plan",
      userSays: "做盘前 / 今晚怎么计划",
      workflow: "system/workflows/pre-market.md",
      packet: "pre-market packet",
      output: "trading day plan",
      status: "available_without_cli",
      note: "可先人工规划，CLI 完成后自动补证据。"
    },
    {
      id: "intraday_check",
      nameZh: "盘中检查",
      nameEn: "Intraday Check",
      userSays: "盘中看 MUU / 现在还能按计划吗",
      workflow: "system/workflows/intraday-guidance-protocol.md",
      packet: "runtime monitor packet",
      output: "intraday guidance sheet",
      status: "waiting_for_cli",
      note: "把盘前计划、认知风险和只读证据映射成 Green / Yellow / Red / No-Trade。"
    },
    {
      id: "trade_review",
      nameZh: "交易复盘",
      nameEn: "Trade Review",
      userSays: "复盘 SNXX / 复盘这笔交易",
      workflow: "system/workflows/post-market.md",
      packet: "contextual trade evidence packet",
      output: "review + lessons",
      status: "available_manual",
      note: "可先复盘，CLI 完成后再补成交易证据包。"
    },
    {
      id: "post_market",
      nameZh: "盘后总结",
      nameEn: "Post-market Review",
      userSays: "盘后复盘 / 今天总结",
      workflow: "system/workflows/post-market.md",
      packet: "post-market packet",
      output: "daily report + HTML",
      status: "available_manual",
      note: "先看 QQQ / VIX / 市场背景，再做盘后总结。"
    },
    {
      id: "company_research",
      nameZh: "公司研究",
      nameEn: "Company Research",
      userSays: "研究 COHR / 研究 ORCL",
      workflow: "system/workflows/company-research.md",
      packet: "company research packet",
      output: "dossier + thesis candidate",
      status: "available_manual",
      note: "短线可以压缩流程，长期研究保持完整。"
    },
    {
      id: "industry_research",
      nameZh: "行业研究",
      nameEn: "Industry Research",
      userSays: "研究 AI GPU / 存储周期",
      workflow: "templates/industry-research.md",
      packet: "industry research packet",
      output: "industry dossier",
      status: "waiting_for_cli",
      note: "用于沉淀世界观、产业链和估值框架。"
    },
    {
      id: "weekly_review",
      nameZh: "周末复盘",
      nameEn: "Weekend Review",
      userSays: "周末复盘",
      workflow: "system/workflows/weekend-review.md",
      packet: "combined packets",
      output: "weekly report",
      status: "available_manual",
      note: "复盘交易、研究质量、系统更新和下周重点。"
    }
  ],
  evidenceGaps: [
    {
      id: "GAP-001",
      severity: "High",
      title: "stock_team CLI 尚未稳定验收",
      detail: "主脑还不能稳定通过统一命令拿到 evidence packets。",
      owner: "Antigravity",
      target: "handoff/requests/antigravity-current-tasks.md"
    },
    {
      id: "GAP-002",
      severity: "High",
      title: "MUU 当前持仓证据未形成 packet",
      detail: "需要 MUU / MU / QQQ / VIX 的盘前与日线证据，以及当前风险数据。",
      owner: "Codex + stock_team after CLI",
      target: "system/data/packets/"
    },
    {
      id: "GAP-003",
      severity: "Medium",
      title: "COHR / ORCL 研究证据包未自动化",
      detail: "已有研究流程，但 peer/company factual packet 还需要固化。",
      owner: "Antigravity",
      target: "company research packet"
    }
  ],
  packets: [
    {
      type: "RS rebound backtest",
      status: "absorbed",
      path: "../wiki/sources/stock-team-rs-pullback-backtest-2026-06-06.md",
      usedIn: "decision/tactics/rs-pullback-rebound-candidate.md"
    },
    {
      type: "Major drawdown report",
      status: "html_ready",
      path: "reports/2026-06-05-major-drawdown-review.html",
      usedIn: "system/traceability/reports-index.json"
    },
    {
      type: "SNXX trade evidence",
      status: "waiting_for_cli_fixture",
      path: "../wiki/journals/2026-06-04-snxx-fill-review.md",
      usedIn: "future contextual trade evidence packet"
    },
    {
      type: "COHR peer packet",
      status: "waiting_for_stock_team",
      path: "../system/data/packets/",
      usedIn: "COHR swing thesis refinement"
    },
    {
      type: "ORCL company packet",
      status: "waiting_for_stock_team",
      path: "../system/data/packets/",
      usedIn: "ORCL company research lifecycle"
    }
  ],
  pendingLessons: [
    {
      id: "CAND-2026-06-06-005",
      title: "RS pullback rebound tactic remains restricted",
      status: "pending_review",
      source: "stock_team RS backtest",
      target: "decision/tactics/rs-pullback-rebound-candidate.md"
    }
  ],
  links: [
    { label: "Growth Dashboard / 认知成长页", href: "growth-dashboard-draft.html" },
    { label: "Intraday Guidance Demo / 盘中引导 Demo", href: "reports/intraday-guidance-demo.html" },
    { label: "Latest Review HTML / 最新复盘报告", href: "reports/2026-06-05-major-drawdown-review.html" },
    { label: "Stock Team Dashboard / 证据引擎面板", href: "file:///D:/gemini/lianghua/stock_team/reports/dashboard.html" }
  ]
};
