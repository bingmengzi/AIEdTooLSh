"""AiEdToolsH 后端服务入口"""
import logging
import logging.handlers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api import health, generate, steps

# 项目根目录（用于日志存放）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # e:/AIPG/AiEdToolsH
LOGS_DIR = PROJECT_ROOT / "logs"


def setup_logging():
    """配置全局日志系统
    
    - app.log: INFO+ 级别，10MB轮转，保留5个备份
    - debug.log: DEBUG+ 级别，包含完整提示词详情
    - 控制台: INFO+ 级别
    """
    # 确保 logs 目录存在
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 日志格式
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 根logger设为DEBUG，由handler控制输出级别
    
    # 清除已有handler（避免重复添加）
    root_logger.handlers.clear()
    
    # 1. app.log - INFO+ 级别，轮转文件
    app_log_path = LOGS_DIR / "app.log"
    app_handler = logging.handlers.RotatingFileHandler(
        filename=str(app_log_path),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)
    
    # 2. debug.log - DEBUG+ 级别（包含完整提示词）
    debug_log_path = LOGS_DIR / "debug.log"
    debug_handler = logging.handlers.RotatingFileHandler(
        filename=str(debug_log_path),
        maxBytes=50 * 1024 * 1024,  # 50MB（debug日志较大）
        backupCount=3,
        encoding="utf-8"
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    root_logger.addHandler(debug_handler)
    
    # 3. 控制台 - INFO+ 级别
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"日志系统初始化完成 | app.log: {app_log_path} | debug.log: {debug_log_path}")


# 在创建 app 之前初始化日志
setup_logging()

app = FastAPI(
    title="AiEdToolsH API",
    description="AI 教育交互动画生成平台",
    version="0.1.0"
)

# CORS 配置 - 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router)
app.include_router(generate.router)
app.include_router(steps.router)

# 挂载静态文件服务
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
outputs_dir = settings.OUTPUTS_DIR

# 生成的HTML文件 (必须在frontend之前挂载，否则会被frontend捕获)
if outputs_dir.exists():
    app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

# 前端页面 - 挂载到根路径
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
