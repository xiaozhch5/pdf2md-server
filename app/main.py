from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router

# 创建FastAPI应用
app = FastAPI(
    title="PDF to Markdown API",
    description="使用marker库将PDF转换为Markdown的API服务",
    version="0.1.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


@app.get("/", tags=["root"])
async def root():
    """API根路径，返回API信息"""
    return {
        "message": "欢迎使用PDF转Markdown API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 