"""
时间类工具（不依赖 Spring Boot 后端，属 Agent 本地能力）

包含：当前时间、时区转换、时间差计算、倒计时、日期解析。

设计说明：
- 时区用标准库 zoneinfo（项目已装 tzdata），支持夏令时的地区也能正确换算；
  若环境缺失 tzdata 则自动降级为固定 UTC+8 偏移。
- 日期解析未引入 python-dateutil，自行实现：既支持显式格式（2026-10-01、2026年10月1日 14:30），
  也支持中文相对表达（今天/明天/后天/昨天/前天、3天后、2小时前、下周一、下午3点）。
"""
import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

try:
    DEFAULT_TZ = ZoneInfo("Asia/Shanghai")  # 中国标准时间
except Exception:  # 环境缺 tzdata 时降级（中国无夏令时，固定 +8 等价）
    DEFAULT_TZ = timezone(timedelta(hours=8))

_WEEKDAY_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

# 时区别名 -> IANA 时区名（LLM 常给中文或城市名，这里做一层友好映射）
_TZ_ALIASES = {
    "北京时间": "Asia/Shanghai", "中国时间": "Asia/Shanghai", "中国": "Asia/Shanghai",
    "北京": "Asia/Shanghai", "上海": "Asia/Shanghai", "china": "Asia/Shanghai",
    "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai", "cst": "Asia/Shanghai",
    "utc": "UTC", "gmt": "UTC",
    "纽约": "America/New_York", "new york": "America/New_York", "newyork": "America/New_York",
    "伦敦": "Europe/London", "london": "Europe/London",
    "东京": "Asia/Tokyo", "tokyo": "Asia/Tokyo", "日本": "Asia/Tokyo",
    "洛杉矶": "America/Los_Angeles", "los angeles": "America/Los_Angeles",
    "巴黎": "Europe/Paris", "paris": "Europe/Paris",
    "柏林": "Europe/Berlin", "悉尼": "Australia/Sydney", "新加坡": "Asia/Singapore",
}

# 显式日期时间格式（按由精确到模糊的顺序尝试）
_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y年%m月%d日 %H:%M:%S", "%Y年%m月%d日 %H:%M", "%Y年%m月%d日 %H点", "%Y年%m月%d日",
    "%m-%d %H:%M", "%m/%d %H:%M", "%m月%d日 %H:%M", "%m月%d日",
    "%H:%M:%S", "%H:%M",
)

_PARSE_HINT = (
    "无法解析该时间。支持的写法示例：2026-10-01、2026-10-01 14:30、2026年10月1日、10月1日 14:30、14:30；"
    "相对表达：今天/明天/后天/昨天/前天、3天后、2小时前、下周一、下午3点。"
)


# ============ 内部辅助函数（不对外暴露为工具） ============

def _resolve_tz(name: str):
    """把时区名/别名/偏移写法解析为 tzinfo；无法识别时抛 ValueError 并给出可用示例。"""
    if not name or not name.strip():
        return DEFAULT_TZ
    key = name.strip()
    low = key.lower()
    if low in _TZ_ALIASES:
        return ZoneInfo(_TZ_ALIASES[low])
    # 固定偏移写法：UTC+8 / UTC-5 / +08:00
    m = re.fullmatch(r"(?:utc|gmt)?\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?", low)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        hours = int(m.group(2))
        minutes = int(m.group(3) or 0)
        return timezone(sign * timedelta(hours=hours, minutes=minutes))
    try:
        return ZoneInfo(key)
    except Exception:
        raise ValueError(
            f"无法识别时区：{name}。可用：Asia/Shanghai、UTC、America/New_York、Europe/London、"
            f"Asia/Tokyo 等 IANA 名称；UTC+8 / UTC-5 这类偏移写法；或中文 北京时间、纽约、伦敦、东京。"
        )


def _extract_time(raw: str):
    """从文本中提取时分；支持 14:30、下午3点、15点30。提取不到返回 None。"""
    m = re.search(r"(上午|早上|早晨|中午|下午|傍晚|晚上|夜里)?\s*(\d{1,2})\s*[点時时]\s*(\d{1,2})?\s*分?", raw)
    if m:
        hour = int(m.group(2))
        minute = int(m.group(3) or 0)
        period = m.group(1)
        if period in ("下午", "傍晚", "晚上", "夜里") and hour < 12:
            hour += 12
        if period == "中午" and hour < 12:
            hour = 12
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", raw)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        second = int(m.group(3) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute, second)
    return None


def _parse_datetime(text: str, base: datetime | None = None) -> datetime:
    """解析日期时间文本（显式格式 + 中文相对表达），失败抛 ValueError。"""
    base = base or datetime.now(DEFAULT_TZ)
    raw = (text or "").strip()
    if not raw:
        raise ValueError("未提供时间文本")

    # A. 星期表达：下下周三 / 下周一 / 本周日 / 周五
    m = re.search(r"(下下|下|本|这)?\s*(?:周|星期|礼拜)\s*([一二三四五六日天1-7])", raw)
    if m:
        week_shift = {"下下": 2, "下": 1, "本": 0, "这": 0}.get(m.group(1) or "本", 0)
        idx_cn = "一二三四五六日天1234567"
        weekday = idx_cn.index(m.group(2)) % 7  # 周一=0 ... 周日=6
        monday = base.date() - timedelta(days=base.date().weekday())
        target = monday + timedelta(days=weekday + 7 * week_shift)
        t = _extract_time(raw) or time(0, 0)
        return datetime.combine(target, t).replace(tzinfo=base.tzinfo)

    # B. 相对天数词
    day_shift = 0
    if "前天" in raw:
        day_shift = -2
    elif "昨天" in raw or "昨日" in raw:
        day_shift = -1
    elif "明天" in raw or "明日" in raw:
        day_shift = 1
    elif "后天" in raw:
        day_shift = 2

    # C. 相对量：N 秒/分钟/小时/天/周/月/年 + 后/前/内
    m = re.search(r"(\d+)\s*(秒钟|秒|分钟|分|小时|时|天|日|周|星期|个月|月|年)\s*(以)?(后|前|内)", raw)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        direction = -1 if m.group(4) == "前" else 1
        delta = {
            "秒钟": timedelta(seconds=n), "秒": timedelta(seconds=n),
            "分钟": timedelta(minutes=n), "分": timedelta(minutes=n),
            "小时": timedelta(hours=n), "时": timedelta(hours=n),
            "天": timedelta(days=n), "日": timedelta(days=n),
            "周": timedelta(weeks=n), "星期": timedelta(weeks=n),
            "个月": timedelta(days=30 * n), "月": timedelta(days=30 * n),
            "年": timedelta(days=365 * n),
        }[unit]
        result = base + direction * delta
        t = _extract_time(raw)
        if t:  # 文本里还带具体时间点（如“3天后下午2点”）则覆盖时分秒
            result = result.replace(hour=t.hour, minute=t.minute, second=t.second, microsecond=0)
        return result

    # D. 显式格式
    for fmt in _TIME_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        if "%Y" not in fmt:  # 未给年份 -> 用基准年份
            dt = dt.replace(year=base.year)
        if "%d" not in fmt:  # 未给日期 -> 用基准日期
            dt = dt.replace(month=base.month, day=base.day)
        if "%H" not in fmt:  # 未给时间 -> 默认 00:00
            dt = dt.replace(hour=0, minute=0, second=0)
        return dt.replace(tzinfo=base.tzinfo)

    # E. 只有时间点 / 只有天数词（如“下午3点”“明天”“明天下午3点”）
    t = _extract_time(raw)
    if t:
        d = base.date() + timedelta(days=day_shift)
        return datetime.combine(d, t).replace(tzinfo=base.tzinfo)
    if day_shift != 0:
        d = base.date() + timedelta(days=day_shift)
        return datetime.combine(d, time(0, 0)).replace(tzinfo=base.tzinfo)

    raise ValueError(_PARSE_HINT)


def _tz_label(dt: datetime) -> str:
    """把时区信息格式化成人类可读文本（名称 + UTC 偏移 + 星期）。"""
    tz = dt.tzinfo
    offset = dt.utcoffset() or timedelta(0)
    total_min = int(offset.total_seconds() // 60)
    sign = "+" if total_min >= 0 else "-"
    hh, mm = divmod(abs(total_min), 60)
    name = getattr(tz, "key", None) or str(tz)
    return f"{name} (UTC{sign}{hh:02d}:{mm:02d}) {_WEEKDAY_CN[dt.weekday()]}"


def _humanize(delta: timedelta) -> str:
    """把时间差格式化为 X天Y小时Z分钟W秒。"""
    total = int(delta.total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}天")
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分钟")
    if seconds or not parts:
        parts.append(f"{seconds}秒")
    return "".join(parts)


# ============ 对外工具 ============

@tool
async def get_current_time() -> str:
    """
    获取当前日期、星期与时间（默认中国标准时间 Asia/Shanghai）。
    当用户问“现在几点”“今天几号”“今天星期几”等与时间相关的问题时调用；
    也可在需要判断“最新/最近/几天内”这类相对时间时先调用它，拿当前时间作参照。
    """
    now = datetime.now(DEFAULT_TZ)
    return f"{now.strftime('%Y年%m月%d日')} {_WEEKDAY_CN[now.weekday()]} {now.strftime('%H:%M:%S')}（中国标准时间 UTC+8）"


@tool
async def convert_timezone(time_str: str, from_tz: str, to_tz: str) -> str:
    """
    把一个时间从源时区换算到目标时区。
    当用户问“纽约现在几点”“北京时间 14:00 是 UTC 几点”“伦敦时间几点”时调用。
    Args:
        time_str: 待换算的时间，支持 2026-10-01 14:30、14:30 等写法；只给时间则默认日期为今天
        from_tz: 源时区，如 Asia/Shanghai、UTC、America/New_York，或中文 北京时间/纽约/伦敦/东京，或 UTC+8
        to_tz: 目标时区，写法同 from_tz
    """
    try:
        src = _resolve_tz(from_tz)
        dst = _resolve_tz(to_tz)
    except ValueError as e:
        return str(e)
    base = datetime.now(src)
    try:
        naive = _parse_datetime(time_str, base=base)
    except ValueError as e:
        return f"时间解析失败：{e}"
    if naive.tzinfo is None:
        naive = naive.replace(tzinfo=src)
    converted = naive.astimezone(dst)
    return (
        f"源时区：{naive.strftime('%Y-%m-%d %H:%M:%S')} {_tz_label(naive)}\n"
        f"目标时区：{converted.strftime('%Y-%m-%d %H:%M:%S')} {_tz_label(converted)}"
    )


@tool
async def calculate_time_difference(start: str, end: str) -> str:
    """
    计算两个时间之间相差多久。当用户问“从 X 到 Y 有多久”“这两个日期差几天”时调用。
    若只关心“距某个未来时间点还有多久”，应改用 countdown。
    Args:
        start: 开始时间，支持 2026-10-01、2026-10-01 14:30、3天前 等写法
        end: 结束时间，写法同 start
    """
    now = datetime.now(DEFAULT_TZ)
    try:
        t1 = _parse_datetime(start, base=now)
        t2 = _parse_datetime(end, base=now)
    except ValueError as e:
        return f"时间解析失败：{e}"
    delta = t2 - t1
    d = abs(delta)
    hours_total = int(d.total_seconds() // 3600)
    minutes_total = int(d.total_seconds() // 60)
    relation = "晚于" if delta.total_seconds() >= 0 else "早于"
    return (
        f"{t1.strftime('%Y-%m-%d %H:%M')} → {t2.strftime('%Y-%m-%d %H:%M')}\n"
        f"相差：{_humanize(d)}（合计 {hours_total} 小时 / {minutes_total} 分钟）\n"
        f"说明：后者{relation}前者"
    )


@tool
async def countdown(target: str) -> str:
    """
    计算距离某个目标时间还有多久（倒计时）。
    当用户问“距离国庆还有多久”“离考试还有几天”“距上线还剩多少时间”时调用。
    Args:
        target: 目标时间，支持 2026-10-01、2026-10-01 08:00、明天下午3点、3天后 等写法
    """
    now = datetime.now(DEFAULT_TZ)
    try:
        t = _parse_datetime(target, base=now)
    except ValueError as e:
        return f"时间解析失败：{e}"
    delta = t - now
    head = f"目标时间：{t.strftime('%Y-%m-%d %H:%M:%S')} {_WEEKDAY_CN[t.weekday()]}"
    if delta.total_seconds() >= 0:
        return f"{head}\n距今还有：{_humanize(delta)}"
    return f"{head}\n已经过去：{_humanize(-delta)}"


@tool
async def parse_date(text: str) -> str:
    """
    把模糊或相对的时间描述解析成确切日期时间。
    当用户说“下周一”“3天后”“明天下午3点”这类表述、需要先转成确切日期再换算时调用。
    Args:
        text: 时间描述，如 2026-10-01、明天下午3点、3天后、下周一、下午3点
    """
    now = datetime.now(DEFAULT_TZ)
    try:
        t = _parse_datetime(text, base=now)
    except ValueError as e:
        return f"时间解析失败：{e}"
    return f"解析结果：{t.strftime('%Y年%m月%d日')} {_WEEKDAY_CN[t.weekday()]} {t.strftime('%H:%M:%S')}"
