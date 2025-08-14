import logging
import sys

# 1. 创建一个日志记录器 (logger)
# 我们给它一个名字，这样整个应用都可以用这同一个实例
logger = logging.getLogger("SoulCommunityLogger")

# 2. 设置日志的最低处理级别
# DEBUG 是最低的，意味着所有级别的日志都会被处理
logger.setLevel(logging.DEBUG)

# 3. 创建一个格式化器 (formatter)
# 这决定了每条日志长什么样子：时间 - 日志名 - 级别 - 模块:行号 - 消息
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
formatter = logging.Formatter(log_format)

# 4. 创建一个处理器 (handler)，用于将日志输出到控制台
# StreamHandler 就是用来输出到终端的
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # 控制台也显示所有级别的日志
console_handler.setFormatter(formatter)

# 5. 创建另一个处理器，用于将日志写入文件（可选，但强烈推荐）
# FileHandler 用于将日志保存到文件中，方便日后排查问题
file_handler = logging.FileHandler("app.log", mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)  # 文件里只记录 INFO 及以上级别，避免文件过大
file_handler.setFormatter(formatter)

# 6. 将处理器添加到日志记录器中
# 这样日志就会同时输出到控制台和文件
logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.info("日志系统初始化成功。")