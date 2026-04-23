"""健康检查路由"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "AiEdToolsH"}

@router.get("/api/providers")
async def list_providers():
    """列出所有AI模型提供商状态"""
    from app.providers import fallback_manager
    providers = await fallback_manager.get_available_providers()
    return {"providers": providers}

@router.get("/api/examples")
async def list_examples():
    """列出所有参考案例"""
    from app.prompts.example_manager import example_manager
    examples = example_manager.list_examples()
    return {"examples": examples, "total": len(examples)}
