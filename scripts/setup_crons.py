"""
设置所有学习循环的定时任务
运行: python3.12 scripts/setup_crons.py
（每次会话开始时可运行以确保cron存在）
"""
# This is documentation - actual crons are set via CronCreate in Claude Code
# The following schedule should be maintained:

SCHEDULE = {
    "harvest_agent": {
        "cron": "35 20 * * 1-5",  # 4:35 PM ET weekdays (20:35 UTC)
        "prompt": "cd ~/stock_team && /tool/pandora/bin/python3.12 agents/harvest_agent.py 2>&1 | tail -20",
        "desc": "每日收盘后记录结果"
    },
    "learning_agent": {
        "cron": "0 21 * * 5",     # 5:00 PM ET Friday (21:00 UTC)
        "prompt": "cd ~/stock_team && /tool/pandora/bin/python3.12 agents/learning_agent.py 2>&1 | tail -30",
        "desc": "每周五重训练模型"
    },
    "health_check": {
        "cron": "0 12 * * 1-5",   # 8:00 AM ET weekdays
        "prompt": "cd ~/stock_team && /tool/pandora/bin/python3.12 agents/health_check.py 2>&1",
        "desc": "每日开盘前健康检查"
    }
}

if __name__ == "__main__":
    print("请在 Claude Code 会话中运行以下 CronCreate 命令来注册定时任务：")
    for name, info in SCHEDULE.items():
        print(f"\n# {info['desc']}")
        print(f"# Cron: {info['cron']}")
        print(f"# Prompt: {info['prompt'][:80]}")
