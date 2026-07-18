import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 1. 创建一个日志记录器 (logger)
# 我们给它一个名字，这样整个应用都可以用这同一个实例
logger = logging.getLogger("SoulCommunityLogger")

# 2. 设置日志的最低处理级别
# DEBUG 是最低的，意味着所有级别的日志都会被处理
logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))

# 3. 创建一个格式化器 (formatter)
# 这决定了每条日志长什么样子：时间 - 日志名 - 级别 - 模块:行号 - 消息
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
formatter = logging.Formatter(log_format)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File logs are opt-in because application logs must never become a second
    # plaintext copy of user-authored content.
    if os.getenv("ENABLE_FILE_LOGGING", "0") == "1":
        file_handler = RotatingFileHandler(
            "app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

logger.info("日志系统初始化成功。")
