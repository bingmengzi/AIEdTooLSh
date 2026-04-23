"""分阶段生成API - 支持前端分步控制"""
import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

# ======== 阶段1: 学科分析 ========

class AnalyzeRequest(BaseModel):
    query: str

@router.post("/api/step/analyze")
async def step_analyze(request: AnalyzeRequest):
    """学科分析（本地关键词匹配，同步返回）"""
    logger.info(f"[阶段1-学科分析] 收到请求 | query={request.query[:100]}{'...' if len(request.query) > 100 else ''}")
    from app.services.subject_analyzer import subject_analyzer
    result = subject_analyzer.analyze(request.query)
    logger.info(f"[阶段1-学科分析] 完成 | subject={result.get('subject')} | branch={result.get('branch')} | scene_type={result.get('scene_type')}")
    return result

# ======== 阶段2: DSL生成 ========

class DSLRequest(BaseModel):
    query: str
    analysis: dict       # 来自阶段1的分析结果
    model: str = ""      # 指定模型，空=自动降级

@router.post("/api/step/dsl")
async def step_dsl(request: DSLRequest):
    """DSL生成（SSE流式）"""
    # 记录入口日志
    analysis_summary = f"subject={request.analysis.get('subject')}, branch={request.analysis.get('branch')}, scene_type={request.analysis.get('scene_type')}"
    logger.info(f"[阶段2-DSL生成] 收到请求 | query={request.query[:80]}... | model={request.model or '自动降级'} | analysis={{{analysis_summary}}}")
    
    from app.services.orchestrator import orchestrator
    
    async def event_stream():
        try:
            async for event in orchestrator.generate_dsl_stream(
                query=request.query,
                analysis=request.analysis,
                model=request.model
            ):
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"DSL生成出错: {e}", exc_info=True)
            error_data = json.dumps({"event": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )

# ======== 阶段3: HTML生成（含Runtime组装） ========

class HTMLRequest(BaseModel):
    query: str
    dsl: dict            # 来自阶段2的DSL结果
    model: str = ""      # 指定模型，空=自动降级

@router.post("/api/step/html")
async def step_html(request: HTMLRequest):
    """HTML生成（SSE流式，内部含Runtime prompt组装 + AI调用 + 后处理 + 保存）"""
    # 记录入口日志
    dsl_summary = f"topic={request.dsl.get('topic')}, scene_type={request.dsl.get('scene_type')}"
    logger.info(f"[阶段3-HTML生成] 收到请求 | query={request.query[:80]}... | model={request.model or '自动降级'} | dsl={{{dsl_summary}}}")
    
    from app.services.orchestrator import orchestrator
    
    async def event_stream():
        try:
            async for event in orchestrator.generate_html_stream(
                query=request.query,
                dsl_data=request.dsl,
                model=request.model
            ):
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"HTML生成出错: {e}", exc_info=True)
            error_data = json.dumps({"event": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )
