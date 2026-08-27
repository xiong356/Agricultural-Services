"""
logger.py
溪山农服平台 — 后端日志系统

功能:
  1. 四级日志: DEBUG / INFO / WARN / ERROR
  2. 控制台实时彩色输出（开发调试用）
  3. 缓冲区 + 定时刷盘（每 5 分钟或缓冲区满 100 条时写入文件）
  4. 按日期轮转（每天一个日志文件，自动保留最近 N 天）
  5. trace_id 请求追踪（每个请求自动生成唯一 ID，贯穿整条调用链）
  6. 结构化格式: 时间戳 | 级别 | 模块:函数:行号 | trace_id | 内容

日志文件:
  位置: backend/logs/app_YYYY-MM-DD.log
  轮转: 每天午夜自动创建新文件
  清理: 自动删除超过 backupCount 天的旧日志

使用方式:
  from logger import get_logger
  logger = get_logger(__name__)
  logger.info("用户登录成功", extra={"user_id": "xxx"})
  logger.error("API 调用失败", extra={"status_code": 500})
"""

import os
import sys
import time
import uuid
import threading
import contextvars
import logging
from datetime import datetime
from logging import (
    LogRecord, Formatter, Filter,
    StreamHandler, DEBUG, INFO, WARNING, ERROR, CRITICAL,
)
from logging.handlers import TimedRotatingFileHandler

# ============================================================
# 配置常量
# ============================================================

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")
_LOG_LEVEL = DEBUG                    # 开发环境: DEBUG; 生产环境: INFO
_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-7s | %(module)s:%(funcName)s:%(lineno)d | "
    "trace_id=%(trace_id)s | %(message)s"
)
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 缓冲区配置
_BUFFER_SIZE = 100                    # 缓冲区满 100 条时刷盘
_FLUSH_INTERVAL = 300                 # 每 300 秒（5 分钟）定时刷盘
_BACKUP_COUNT = 7                     # 保留最近 7 天的日志文件

# ============================================================
# trace_id 上下文管理（支持 async/await）
# ============================================================

_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default="-"
)


def get_trace_id() -> str:
    """获取当前请求的 trace_id"""
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> contextvars.Token:
    """设置 trace_id，返回 token 用于恢复"""
    return _trace_id_var.set(trace_id)


def reset_trace_id(token: contextvars.Token):
    """恢复 trace_id 到之前的值"""
    _trace_id_var.reset(token)


def new_trace_id() -> str:
    """生成新的 trace_id"""
    return f"req_{uuid.uuid4().hex[:12]}"


# ============================================================
# TraceId 过滤器 — 将 trace_id 注入到每条日志记录
# ============================================================

class TraceIdFilter(Filter):
    """将 contextvars 中的 trace_id 注入到 LogRecord"""
    def filter(self, record: LogRecord) -> bool:
        record.trace_id = _trace_id_var.get()
        return True


# ============================================================
# 彩色控制台格式化器
# ============================================================

class ColoredFormatter(Formatter):
    """控制台彩色输出 — 不同级别用不同颜色"""

    # ANSI 颜色码
    _COLORS = {
        DEBUG:     "\033[36m",   # 青色
        INFO:      "\033[32m",   # 绿色
        WARNING:   "\033[33m",   # 黄色
        ERROR:     "\033[31m",   # 红色
        CRITICAL:  "\033[35m",   # 紫色
    }
    _RESET = "\033[0m"
    _BOLD = "\033[1m"

    def format(self, record: LogRecord) -> str:
        color = self._COLORS.get(record.levelno, "")
        # 时间戳灰色，级别带颜色，其余正常
        formatted = super().format(record)
        # 给级别加颜色
        level_name = record.levelname
        colored_level = f"{color}{level_name:<7}{self._RESET}"
        formatted = formatted.replace(level_name, colored_level, 1)
        return formatted


# ============================================================
# 缓冲定时文件处理器
# ============================================================

class BufferedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    带缓冲区的定时轮转文件处理器

    特性:
      - 日志记录先存入内存缓冲区，不立即写磁盘
      - 缓冲区满 _BUFFER_SIZE 条 → 立即刷盘
      - 每 _FLUSH_INTERVAL 秒 → 定时刷盘
      - WARN 及以上级别 → 立即刷盘（不等待缓冲）
      - 每天午夜自动轮转，旧文件重命名为 app.YYYY-MM-DD.log
      - 自动删除超过 _BACKUP_COUNT 天的日志文件
    """

    def __init__(
        self,
        filename,
        when="midnight",
        interval=1,
        backupCount=_BACKUP_COUNT,
        buffer_size=_BUFFER_SIZE,
        flush_interval=_FLUSH_INTERVAL,
        **kwargs,
    ):
        super().__init__(
            filename, when=when, interval=interval,
            backupCount=backupCount, **kwargs
        )
        self._buffer: list[LogRecord] = []
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._lock_buffer = threading.Lock()
        self._timer: threading.Timer | None = None
        self._start_flush_timer()

    def _start_flush_timer(self):
        """启动定时刷盘线程"""
        self._timer = threading.Timer(self._flush_interval, self._flush_buffer)
        self._timer.daemon = True
        self._timer.start()

    def _flush_buffer(self):
        """将缓冲区中的日志记录写入文件"""
        with self._lock_buffer:
            if not self._buffer:
                # 缓冲区空，重启定时器
                self._start_flush_timer()
                return
            records = self._buffer[:]
            self._buffer.clear()

        # 在锁外写入文件，避免长时间持锁
        for record in records:
            super().emit(record)

        # 重启定时器
        self._start_flush_timer()

    def emit(self, record: LogRecord):
        """
        重写 emit：先入缓冲区
        WARN 及以上级别立即刷盘
        """
        # ERROR 及以上 → 立即写入，确保不丢失
        if record.levelno >= WARNING:
            with self._lock_buffer:
                # 先把缓冲区里的都写出去
                pending = self._buffer[:]
                self._buffer.clear()
            for r in pending:
                super().emit(r)
            super().emit(record)
            return

        # DEBUG / INFO → 入缓冲区
        with self._lock_buffer:
            self._buffer.append(record)
            should_flush = len(self._buffer) >= self._buffer_size

        if should_flush:
            self._flush_buffer()

    def close(self):
        """关闭前刷出剩余缓冲"""
        if self._timer:
            self._timer.cancel()
        self._flush_buffer()
        super().close()


# ============================================================
# 日志系统初始化
# ============================================================

def _ensure_log_dir():
    """确保日志目录存在"""
    if not os.path.exists(_LOG_DIR):
        os.makedirs(_LOG_DIR, exist_ok=True)


def _setup_root_logger() -> logging.Logger:
    """
    配置根日志器:
      - 控制台 handler: 实时彩色输出（DEBUG 及以上）
      - 文件 handler: 缓冲 + 定时刷盘 + 每日轮转
    """
    _ensure_log_dir()

    # 使用 logging.getLogger 注册到全局 logger 树，确保 getChild 正常工作
    root_logger = logging.getLogger("xishan")
    root_logger.setLevel(_LOG_LEVEL)
    root_logger.propagate = False

    # 避免重复添加 handler（热重载时可能多次初始化）
    if root_logger.handlers:
        return root_logger

    trace_filter = TraceIdFilter()

    # --- 控制台 Handler（实时输出） ---
    console_handler = StreamHandler(sys.stdout)
    console_handler.setLevel(_LOG_LEVEL)
    console_handler.setFormatter(ColoredFormatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT))
    console_handler.addFilter(trace_filter)
    root_logger.addHandler(console_handler)

    # --- 文件 Handler（缓冲 + 每日轮转） ---
    file_handler = BufferedTimedRotatingFileHandler(
        filename=_LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=_BACKUP_COUNT,
        buffer_size=_BUFFER_SIZE,
        flush_interval=_FLUSH_INTERVAL,
        encoding="utf-8",
    )
    file_handler.setLevel(_LOG_LEVEL)
    file_handler.setFormatter(Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FORMAT))
    file_handler.addFilter(trace_filter)
    root_logger.addHandler(file_handler)

    return root_logger


# 全局根日志器（单例）
_root_logger = _setup_root_logger()

# 子日志器缓存
_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str = __name__) -> logging.Logger:
    """
    获取指定模块的日志器

    Args:
        name: 模块名（通常传 __name__）

    Returns:
        Logger 实例

    使用方式:
        from logger import get_logger
        logger = get_logger(__name__)
        logger.info("服务启动")
        logger.debug("调试信息", extra={"key": "value"})
    """
    if name in _loggers:
        return _loggers[name]

    # 使用全局 logger 树中的 getChild，确保 propagate 链正确
    child = logging.getLogger(f"xishan.{name}")
    _loggers[name] = child
    return child


# ============================================================
# 便捷函数
# ============================================================

def log_request(method: str, path: str, status_code: int, duration_ms: float):
    """记录 HTTP 请求日志"""
    logger = get_logger("request")
    msg = f"{method} {path} → {status_code} ({duration_ms:.0f}ms)"
    if status_code >= 500:
        logger.error(msg)
    elif status_code >= 400:
        logger.warning(msg)
    else:
        logger.info(msg)
