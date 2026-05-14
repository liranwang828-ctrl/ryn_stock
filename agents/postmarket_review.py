"""
收盘复盘 agent — 基于 session_log 进行有根据的讨论
核心原则：先列出已知/未知条件，再讨论，不武断假设
"""
import sys, os, json, glob
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")

MASTER_PERSPECTIVES = {
    "Minervini":     "技术面/趋势/SEPA策略",
    "Buffett":       "基本面/护城河/长期价值",
    "Druckenmiller": "宏观/流动性/美联储",
    "Marks":         "市场周期/第二层思维/风险控制",
    "Burry":         "反共识/基本面深度/论点失效止损",
    "Taleb":         "尾部风险/仓位管理/反脆弱",
}

def load_session_log(date_str=None):
    """加载今日交易日记"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(KNOWLEDGE_DIR, f"session_{date_str}.md")
    if os.path.exists(path):
        return open(path).read()
    return None

def load_methodology():
    """加载历史方法论知识库"""
    path = os.path.join(KNOWLEDGE_DIR, "trading_methodology.md")
    return open(path).read() if os.path.exists(path) else ""

def extract_unknowns(session_log):
    """从 session_log 提取未知条件"""
    unknowns = []
    for line in session_log.split('\n'):
        if line.strip().startswith('- ❓'):
            unknowns.append(line.strip()[4:].strip())
    return unknowns

def generate_review_prompt(session_log, methodology):
    """生成复盘讨论的结构化 prompt"""
    unknowns = extract_unknowns(session_log)

    prompt = f"""
## 收盘复盘协议

### 已知信息（来自 session_log）
{session_log}

### 历史方法论参考
{methodology[:1000]}

### 复盘规则（所有 agent 必须遵守）
1. **先列未知条件**：每个 agent 发言前，必须明确标注自己在哪些假设上讨论
2. **不武断归因**：如果缺少用户操作记录，说"在不知道入场时间的前提下"
3. **条件性结论**：结论必须附带条件，例如"如果用户在10:30之后入场，则..."
4. **知识提炼**：讨论结束后提炼出可复用的方法论

### 当前已知的未知条件
"""
    for i, u in enumerate(unknowns):
        prompt += f"{i+1}. {u}\n"

    prompt += "\n### 今日待讨论问题\n"
    # 提取用户问题
    in_questions = False
    for line in session_log.split('\n'):
        if '盘后问题' in line:
            in_questions = True
        elif in_questions and line.strip().startswith('-'):
            prompt += f"{line}\n"

    return prompt

def run_review(date_str=None):
    """运行收盘复盘"""
    session = load_session_log(date_str)
    if not session:
        print(f"未找到 {date_str or '今日'} 的交易日记")
        print(f"请先填写: {KNOWLEDGE_DIR}/session_{date_str or datetime.now().strftime('%Y-%m-%d')}.md")
        return

    methodology = load_methodology()
    unknowns = extract_unknowns(session)

    print(f"{'='*60}")
    print(f"  收盘复盘  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print()
    print("【Step 1: 确认未知条件（讨论前必须明确）】")
    print()
    for i, u in enumerate(unknowns, 1):
        print(f"  {i}. {u}")
    print()
    print("─── 各大师发言前声明适用条件 ───")
    print()

    # 从 session_log 提取问题
    questions = []
    in_q = False
    for line in session.split('\n'):
        if '盘后问题' in line: in_q = True
        elif in_q and line.strip().startswith('-'): questions.append(line.strip()[1:].strip())

    for i, q in enumerate(questions, 1):
        print(f"【用户问题 {i}】{q}")
        print()
        # 每个大师基于已知条件给出有条件的回答
        for master, specialty in MASTER_PERSPECTIVES.items():
            print(f"  [{master}（{specialty}）]")
            print(f"  前提假设：基于 session_log 记录，未知用户精确入场时间和仓位")
            # 这里实际应该调用 LLM，现在用占位符
            print(f"  → [待实际 agent 填充，基于 session_log 数据]")
            print()
        print()

if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    run_review(date_str)
