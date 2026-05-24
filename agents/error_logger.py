"""
统一错误处理标准
用法:
  from agents.error_logger import log_error, safe_run

  # 方式1: 装饰器
  @safe_run(default=None, label="CIO分析")
  def my_func(): ...

  # 方式2: 直接记录
  log_error("harvest_agent", "yfinance timeout", {"sym": "MRVL"})
"""
import os, json, traceback, functools
from datetime import datetime, timezone

BASE      = ((os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__))) if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if any(x in os.path.abspath(__file__) for x in ["agents", "tests", "scripts", "archive"]) else os.path.dirname(os.path.abspath(__file__)), "templates")) else os.path.expanduser("~/stock_team"))
ERROR_LOG = os.path.join(BASE, "learning", "errors.jsonl")

def log_error(source: str, msg: str, data: dict = None, exc: Exception = None):
    """写入错误到 learning/errors.jsonl，供 health_check 检测"""
    os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
    entry = {
        "ts":     datetime.now(timezone.utc).isoformat(),
        "source": source,
        "msg":    str(msg)[:200],
        "data":   data or {},
        "tb":     traceback.format_exc()[-500:] if exc else "",
    }
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def get_recent_errors(hours=24) -> list:
    """读取最近N小时的错误"""
    if not os.path.exists(ERROR_LOG):
        return []
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    errors = []
    for line in open(ERROR_LOG, encoding="utf-8"):
        try:
            e = json.loads(line)
            ts = datetime.fromisoformat(e["ts"])
            if ts > cutoff:
                errors.append(e)
        except Exception:
            pass
    return errors

def safe_run(default=None, label="", reraise=False):
    """装饰器：捕获异常 → 记录到 errors.jsonl → 返回 default"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                src = label or func.__name__
                log_error(src, str(e), exc=e)
                if reraise:
                    raise
                return default
        return wrapper
    return decorator

YF_STATUS_FILE = os.path.join(BASE, "logs", "yfinance_status.json")

def record_yfinance_status(symbol: str, success: bool, error_msg: str = None):
    """记录 yfinance 数据抓取成功/失败状态，供 Dashboard 全局显示"""
    os.makedirs(os.path.dirname(YF_STATUS_FILE), exist_ok=True)
    status_data = {"status": "stable", "last_update": datetime.now(timezone.utc).isoformat(), "errors": []}
    
    if os.path.exists(YF_STATUS_FILE):
        try:
            with open(YF_STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except Exception:
            pass

    errors_list = status_data.get("errors", [])
    
    if not success:
        err_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "sym": symbol.upper(),
            "msg": str(error_msg or "Yahoo Finance connection issue or rate limit")
        }
        # 避免完全重复的最新错误扎堆
        if not errors_list or errors_list[0].get("sym") != err_entry["sym"] or errors_list[0].get("msg") != err_entry["msg"]:
            errors_list.insert(0, err_entry)
        errors_list = errors_list[:15]  # 保留最近15次错误
    
    # 过滤掉超过2小时的错误
    from datetime import timedelta
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    valid_errors = []
    has_recent_error = False
    
    for err in errors_list:
        try:
            err_time = datetime.fromisoformat(err["ts"])
            if err_time > two_hours_ago:
                has_recent_error = True
            if err_time > (datetime.now(timezone.utc) - timedelta(hours=24)):
                valid_errors.append(err)
        except Exception:
            pass
            
    status_data["errors"] = valid_errors
    status_data["status"] = "restricted" if has_recent_error else "stable"
    status_data["last_update"] = datetime.now(timezone.utc).isoformat()
    if success and not has_recent_error:
        status_data["last_success"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(YF_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

