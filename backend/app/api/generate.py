"""生成接口 - SSE流式输出"""
import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    query: str
    dsl_model: str = ""    # DSL生成阶段指定模型，空=自动降级
    html_model: str = ""   # HTML生成阶段指定模型，空=自动降级


@router.post("/api/generate")
async def generate(request: GenerateRequest):
    """流式生成教学交互页面
    
    接收用户输入，通过SSE返回整个生成过程的实时事件流。
    前端通过 fetch + ReadableStream 接收。
    """
    # 记录请求入口日志
    logger.info(f"收到生成请求 | query={request.query[:100]}{'...' if len(request.query) > 100 else ''} | dsl_model={request.dsl_model or '自动降级'} | html_model={request.html_model or '自动降级'}")
    
    async def event_stream():
        try:
            async for event in orchestrator.generate_stream(
                    request.query,
                    dsl_model=request.dsl_model,
                    html_model=request.html_model
                ):
                # 将每个事件格式化为SSE格式
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            
            # 发送结束标记
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"生成流出错: {e}", exc_info=True)
            error_data = json.dumps({"event": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        }
    )


@router.get("/api/results")
async def list_results():
    """列出最近的生成结果"""
    from app.storage.file_store import file_store
    results = file_store.list_results()
    return {"results": results}
