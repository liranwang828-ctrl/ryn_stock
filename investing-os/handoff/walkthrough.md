# Pre-Market Environment Packet & Plan Evidence Packet 对齐与验证报告

本报告记录了 **Stage 0 (market-context)** 和 **Stage 1 (premarket)** 的所有优化、开发、调试与自动化测试对齐验证。

---

## 1. Stage 0 (market-context) 优化与修复

### 1.1 修复 Offline-Fixture 模式下的 `UnboundLocalError`
* **问题现象**：执行带 `--offline-fixture` 的命令时，抛出 `UnboundLocalError`。
* **修复内容**：将 `universe` 和 `universe_quality` 的读取与解析整体上移到 `handle_market_context` 的最顶部，使其作为通用依赖项在 `if/else` 分支之前完成解析。

### 1.2 优化 Input Mapping 逻辑，防止 Guessing
* **修复内容**：只在 watchlist 简单列表场景下进行元数据默认值补全。若脑端传入结构化 dict 但缺失 `theme` 等字段，将不予自动填充猜测，使其被 `_universe_quality` 精确识别为 Gap 并在 relevance map 中以 `—` 占位，符合审计逻辑。

---

## 2. Stage 1 (premarket) 开发与契约返修对齐

我们完成了 **Stage 1 (premarket)** 的开发与契约（Contract Review）返修对齐，彻底打通了数据、逻辑与输出格式的严格边界约束。

### 2.1 契约返修修正点
根据 Codex 及用户的 Review 意见，我们进行了以下针对性返修：
1. **去除盘中就绪误导**：
   - 移除了 `preauthorized_conditions_met` 输出。
   - 盘前命令仅做数据与规则就绪审计，返回值严格限制在 `required_data_available`（若数据可用）或 `required_data_missing` 或 `preauthorized_definition_complete`，不越权判定盘中执行。
2. **去除心理解释与动机猜想**：
   - `loss_repair_guard` 碰撞逻辑由心理动机词汇改为了客观物理事实表述。
   - 输出统一为：`linked_leveraged_exposure_detected: true; related_position: MUU`。
3. **数据状态（Status）降级与披露**：
   - 当检测到使用 `yfinance` 缓存或 fallback 历史数据源时，将 packet 的 YAML 状态自动由 `status: verified` 降级为 `status: fallback_data`。
   - 在 `warnings` 中准确添加披露：`polygon_api_key_missing_or_failed; fell back to yfinance sandbox data which is not production grade`。
4. **细化 Stale 鲜活度描述**：
   - 如果模拟日期与运行日期不同，不直接写 `Stale: false`。
   - 输出详细的 freshness 描述，如：`Stale: true (simulated date 2026-06-06; cache generated at 2026-06-07T05:58:51.283893+00:00)`。

### 2.2 环境传递与路径修正
* **修复 `BASE` 路径不一致问题**：修正了 `premarket.py` 因模板文件缺失而回退至 `C:\Users\rriww\stock_team` 的 BASE 路径，将其统一对齐至项目根目录 `D:\gemini\lianghua\stock_team`。
* **打通 `PREMARKET_DATE` 环境变量传递**：cli 传递 `PREMARKET_DATE` 环境变量给 `premarket.py` 子进程，使盘前抓取与回测分析均保存至一致的模拟日期。

---

## 3. 自动化测试验证 (10/10 Passed)

在 `test_cli.py` 中新增了 `test_cli_premarket_generation` 用以覆盖对焦点池、脑端规则、技术指标及杠杆仓位碰撞的校验。另外新增了 `test_cli_premarket_generation_no_watchlist` 用以验证当不提供 `--watchlist` 参数时直接从决策单中提取焦点池的行为。

在 workspace `d:\gemini\lianghua` 下执行 pytest，所有 10 项单元测试已全部通过：

```bash
pytest stock_team/tests/unit/core/test_cli.py
```

**测试输出**：
```
============================= test session starts =============================
platform win32 -- Python 3.10.11, pytest-9.0.3, pluggy-1.6.0
rootdir: D:\gemini\lianghua\stock_team
configfile: pytest.ini
plugins: anyio-4.13.0
collected 10 items

stock_team\tests\unit\core\test_cli.py ..........                        [100%]

============================= 10 passed in 23.47s =============================
```

---

## 4. 最终 Stage 1 输出 packet 格式校验

生成的 [plan-evidence-packet.md](file:///C:/Users/rriww/Documents/investing-os/system/data/packets/plan-evidence-packet.md) 完美匹配了脑端主控契约：
* **无买卖决策建议**：严格避免了 buy/sell/hold 词汇、仓位调整或心理状态解释。
* **YAML 头完整性**：带有全部 `packet_type`、`status: fallback_data`、`missing_data`、`warnings` 以及 `forbidden_sections_absent` 自审声明。
* **规则碰撞验证**：
  - MU 规则 `loss_repair_guard` 成功触发并记录了 `MUU` 仓位碰撞，生成了 `linked_leveraged_exposure_detected: true; related_position: MUU`。
  - NVDA 规则 `preauthorized_action_fast_check` 触发并正确评估为 `required_data_available`。
