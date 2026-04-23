"""流程编排器 - 串联 分析→DSL→Runtime 全流程"""
import json
import logging
from typing import AsyncGenerator

from app.services.subject_analyzer import subject_analyzer
from app.services.html_extractor import html_extractor
from app.dsl.schema import SceneDSL
from app.dsl.validator import dsl_validator
from app.runtime.engine import runtime_engine
from app.runtime.post_processor import post_processor
from app.providers import fallback_manager
from app.prompts.manager import prompt_manager
from app.storage.file_store import file_store

logger = logging.getLogger(__name__)


class Orchestrator:
    """编排器：管理完整的生成流程"""
    
    async def generate_stream(self, query: str, dsl_model: str = "", html_model: str = "") -> AsyncGenerator[dict, None]:
        """完整的流式生成流程
        
        流程：
        1. 学科分析
        2. DSL生成（调用AI）
        3. DSL校验
        4. Runtime渲染（调用AI，流式）
        5. HTML后处理
        6. 保存结果
        
        Args:
            query: 用户输入
            dsl_model: DSL生成阶段指定模型，空则自动降级
            html_model: HTML生成阶段指定模型，空则自动降级
        
        Yields:
            dict: SSE事件对象，前端根据event字段区分阶段
        """
        html_chunks = []  # 收集所有HTML块
        final_provider = ""
        
        try:
            # ============ 阶段1: 学科分析 ============
            logger.info(f"[阶段1] 学科分析开始 | query={query[:80]}...")
            yield {"event": "analysis_start", "message": "正在分析题目..."}
            
            analysis = subject_analyzer.analyze(query)
            
            logger.info(f"[阶段1] 学科分析完成 | subject={analysis['subject']} | branch={analysis['branch']} | scene_type={analysis['scene_type']} | confidence={analysis['confidence']}")
            
            yield {
                "event": "analysis_done",
                "subject": analysis["subject"],
                "branch": analysis["branch"],
                "scene_type": analysis["scene_type"],
                "confidence": analysis["confidence"],
                "keywords_matched": analysis["keywords_matched"]
            }
            
            # ============ 阶段2: DSL生成 ============
            logger.info(f"[阶段2] DSL生成开始 | model={dsl_model or '自动降级'}")
            yield {"event": "dsl_start", "message": "正在生成场景描述..."}
            
            # 构建DSL生成的prompt
            dsl_prompt = self._build_dsl_prompt(query, analysis)
            
            # 记录 prompt 信息
            system_len = sum(len(m["content"]) for m in dsl_prompt if m["role"] == "system")
            user_len = sum(len(m["content"]) for m in dsl_prompt if m["role"] == "user")
            logger.info(f"[阶段2] DSL prompt 构建完成 | system_chars={system_len} | user_chars={user_len}")
            
            # DEBUG: 记录完整 prompt 内容
            for msg in dsl_prompt:
                if msg["role"] == "system":
                    logger.debug(f"[阶段2] DSL System Prompt 全文:\n{msg['content']}")
                elif msg["role"] == "user":
                    logger.debug(f"[阶段2] DSL User Prompt 全文:\n{msg['content']}")
            
            yield {
                "event": "dsl_prompt",
                "prompt_preview": dsl_prompt[-1]["content"][:300] + "...",
                "full_messages": dsl_prompt  # 完整的 messages 列表
            }
            
            # 调用AI生成DSL（根据 dsl_model 选择调用方式）
            dsl_response_chunks = []
            dsl_provider = ""
            
            if dsl_model:
                # 使用指定模型（不降级）
                stream = fallback_manager.chat_stream_single(
                    provider_name=dsl_model,
                    messages=dsl_prompt,
                    temperature=0.3,
                    max_tokens=2048
                )
            else:
                # 自动降级
                stream = fallback_manager.chat_stream_with_fallback(
                    messages=dsl_prompt,
                    temperature=0.3,
                    max_tokens=2048
                )
            
            async for event in stream:
                if event["event"] == "chunk":
                    dsl_response_chunks.append(event["content"])
                    dsl_provider = event["provider"]
                elif event["event"] == "provider_start":
                    yield {"event": "dsl_provider", "provider": event["provider"], "model": event.get("model", "")}
                elif event["event"] == "all_failed":
                    yield {"event": "error", "stage": "dsl", "message": event["error"]}
                    return
            
            dsl_raw = "".join(dsl_response_chunks)
            
            # DEBUG: 记录 AI 返回的完整 DSL 内容
            logger.debug(f"[阶段2] AI返回的DSL原文:\n{dsl_raw}")
            
            # 校验DSL
            dsl, errors = dsl_validator.validate_and_parse(dsl_raw)
            
            if dsl is None:
                logger.warning(f"[阶段2] DSL校验失败: {errors} | 使用降级方案")
                dsl = dsl_validator.create_fallback_dsl(
                    analysis["subject"], analysis["branch"],
                    query, analysis["scene_type"]
                )
                yield {"event": "dsl_fallback", "errors": errors, "message": "DSL校验失败，使用默认配置"}
            else:
                logger.info(f"[阶段2] DSL校验成功 | topic={dsl.topic} | scene_type={dsl.scene_type.value}")
            
            yield {
                "event": "dsl_done",
                "dsl": dsl.model_dump(),
                "provider": dsl_provider,
                "raw_preview": dsl_raw[:300] + "..." if len(dsl_raw) > 300 else dsl_raw
            }
            
            # ============ 阶段3: Runtime渲染 ============
            logger.info(f"[阶段3] Runtime渲染开始 | scene_type={dsl.scene_type.value} | topic={dsl.topic} | model={html_model or '自动降级'}")
            yield {"event": "runtime_start", "scene_type": dsl.scene_type.value, "topic": dsl.topic}
            
            async for event in runtime_engine.render_stream(dsl, query=query, model=html_model):
                if event["event"] == "chunk":
                    html_chunks.append(event["content"])
                    final_provider = event.get("provider", final_provider)
                elif event["event"] == "all_failed":
                    yield {
                        "event": "error",
                        "stage": "runtime",
                        "message": event.get("error", "所有AI模型均不可用")
                    }
                    return
                # 转发所有事件给前端
                yield event
            
            # ============ 阶段4: 后处理 + 保存 ============
            logger.info(f"[阶段4] 后处理开始 | raw_html_len={len(''.join(html_chunks))}")
            yield {"event": "postprocess_start", "message": "正在处理生成结果..."}
            
            raw_html = "".join(html_chunks)
            
            # DEBUG: 记录 AI 返回的完整 HTML 内容
            logger.debug(f"[阶段4] AI返回的HTML原文:\n{raw_html}")
            
            clean_html = html_extractor.extract_html(raw_html)
            final_html = post_processor.process(clean_html)
            
            logger.info(f"[阶段4] HTML后处理完成 | raw_len={len(raw_html)} | clean_len={len(clean_html)} | final_len={len(final_html)}")
            
            # 保存到本地
            result_id = file_store.save_html(
                html_content=final_html,
                query=query,
                dsl=dsl.model_dump(),
                provider=final_provider
            )
            
            logger.info(f"[阶段4] 结果保存完成 | result_id={result_id} | html_length={len(final_html)} | provider={final_provider}")
            
            yield {
                "event": "complete",
                "result_id": result_id,
                "html_url": f"/outputs/{result_id}.html",
                "provider": final_provider,
                "html_length": len(final_html)
            }
            
        except Exception as e:
            logger.error(f"生成流程出错: {e}", exc_info=True)
            yield {"event": "error", "stage": "unknown", "message": str(e)}
    
    def _build_dsl_prompt(self, query: str, analysis: dict) -> list[dict]:
        """构建DSL生成的prompt"""
        from app.dsl.schema import SceneDSL
        
        system_prompt = """你是一个教育场景分析专家。你需要根据用户输入的教育主题，生成一个结构化的场景描述(Scene DSL)。

请严格按照以下JSON格式输出，不要输出任何其他内容：

```json
{
    "subject": "math",              // 学科: math/physics/chemistry
    "branch": "geometry",            // 分支: geometry/algebra/optics/mechanics等
    "topic": "勾股定理",             // 主题名称
    "description": "展示...",        // 场景描述
    "scene_type": "canvas_interactive", // 场景类型: canvas_interactive/threejs_3d/step_derivation/hybrid
    "layout": "left_canvas_right_panel", // 布局
    "tech_stack": {
        "canvas_2d": true,
        "threejs": false,
        "mathjax": false,
        "tailwind": true,
        "fontawesome": true
    },
    "interactions": {
        "draggable": true,
        "sliders": true,
        "step_buttons": false,
        "animation_controls": false,
        "data_recording": false,
        "theme_switch": false
    },
    "animations": {
        "has_animation": true,
        "animation_type": "interactive",
        "description": "拖拽改变参数，实时更新图形"
    },
    "key_concepts": ["a² + b² = c²"],
    "visual_elements": ["直角三角形", "正方形面积"],
    "parameters": [
        {"name": "边长a", "min": 2, "max": 10, "default": 3}
    ],
    "learning_objectives": ["理解勾股定理"]
}
```

场景类型选择规则：
- canvas_interactive: 2D几何、函数图像、物理模拟（如勾股定理、凸透镜成像）
- threejs_3d: 立体几何、空间向量、分子结构（如三棱锥、四面体）
- step_derivation: 纯证明推导题
- hybrid: 需要3D模型+步骤推导的组合题"""

        user_prompt = f"""请为以下教育主题生成 Scene DSL：

主题：{query}
识别学科：{analysis['subject']}
识别分支：{analysis['branch']}
建议场景类型：{analysis['scene_type']}
匹配关键词：{', '.join(analysis.get('keywords_matched', []))}

请输出JSON格式的Scene DSL。"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    async def generate_dsl_stream(self, query: str, analysis: dict, model: str = "") -> AsyncGenerator[dict, None]:
        """独立的DSL生成阶段
        
        Yields:
            {"event": "dsl_start"}
            {"event": "dsl_prompt", "prompt_preview": "...", "full_messages": [...]}
            {"event": "dsl_provider", "provider": "...", "model": "..."}
            {"event": "dsl_done", "dsl": {...}, "provider": "...", "raw_preview": "..."}
            {"event": "error", "stage": "dsl", "message": "..."}
        """
        logger.info(f"[DSL生成流] 开始 | query={query[:80]}... | model={model or '自动降级'}")
        yield {"event": "dsl_start", "message": "正在生成场景描述..."}
        
        # 构建DSL prompt
        dsl_prompt = self._build_dsl_prompt(query, analysis)
        
        # 记录 prompt 信息
        system_len = sum(len(m["content"]) for m in dsl_prompt if m["role"] == "system")
        user_len = sum(len(m["content"]) for m in dsl_prompt if m["role"] == "user")
        logger.info(f"[DSL生成流] prompt 构建完成 | system_chars={system_len} | user_chars={user_len}")
        
        # DEBUG: 记录完整 prompt 内容
        for msg in dsl_prompt:
            if msg["role"] == "system":
                logger.debug(f"[DSL生成流] System Prompt 全文:\n{msg['content']}")
            elif msg["role"] == "user":
                logger.debug(f"[DSL生成流] User Prompt 全文:\n{msg['content']}")
        
        yield {
            "event": "dsl_prompt",
            "prompt_preview": dsl_prompt[-1]["content"][:300] + "...",
            "full_messages": dsl_prompt
        }
        
        # 调用AI
        dsl_response_chunks = []
        dsl_provider = ""
        
        if model:
            stream = fallback_manager.chat_stream_single(model, dsl_prompt, temperature=0.3, max_tokens=2048)
        else:
            stream = fallback_manager.chat_stream_with_fallback(dsl_prompt, temperature=0.3, max_tokens=2048)
        
        async for event in stream:
            if event["event"] == "chunk":
                dsl_response_chunks.append(event["content"])
                dsl_provider = event["provider"]
            elif event["event"] == "provider_start":
                yield {"event": "dsl_provider", "provider": event["provider"], "model": event.get("model", "")}
            elif event["event"] == "all_failed":
                yield {"event": "error", "stage": "dsl", "message": event["error"]}
                return
        
        dsl_raw = "".join(dsl_response_chunks)
        
        # DEBUG: 记录 AI 返回的完整 DSL 内容
        logger.debug(f"[DSL生成流] AI返回的DSL原文:\n{dsl_raw}")
        
        # 校验DSL
        dsl, errors = dsl_validator.validate_and_parse(dsl_raw)
        
        if dsl is None:
            logger.warning(f"[DSL生成流] DSL校验失败: {errors} | 使用降级方案")
            dsl = dsl_validator.create_fallback_dsl(
                analysis["subject"], analysis["branch"],
                query, analysis["scene_type"]
            )
            yield {"event": "dsl_fallback", "errors": errors, "message": "DSL校验失败，使用默认配置"}
        else:
            logger.info(f"[DSL生成流] DSL校验成功 | topic={dsl.topic} | scene_type={dsl.scene_type.value}")
        
        yield {
            "event": "dsl_done",
            "dsl": dsl.model_dump(),
            "provider": dsl_provider,
            "raw_preview": dsl_raw[:300] + "..." if len(dsl_raw) > 300 else dsl_raw
        }

    async def generate_html_stream(self, query: str, dsl_data: dict, model: str = "") -> AsyncGenerator[dict, None]:
        """独立的HTML生成阶段（含Runtime组装 + AI调用 + 后处理 + 保存）
        
        Yields:
            {"event": "runtime_start", ...}
            {"event": "render_start", ...}
            {"event": "prompt_built", ...}
            {"event": "provider_start", ...}
            {"event": "chunk", ...}
            {"event": "done", ...}
            {"event": "postprocess_start", ...}
            {"event": "complete", ...}
        """
        # 从dict重建SceneDSL对象
        try:
            dsl = SceneDSL(**dsl_data)
            logger.info(f"[HTML生成流] DSL解析成功 | topic={dsl.topic} | scene_type={dsl.scene_type.value}")
        except Exception as e:
            logger.error(f"[HTML生成流] DSL数据无效: {e}")
            yield {"event": "error", "stage": "runtime", "message": f"DSL数据无效: {e}"}
            return
        
        html_chunks = []
        final_provider = ""
        
        # Runtime阶段
        logger.info(f"[HTML生成流] Runtime渲染开始 | scene_type={dsl.scene_type.value} | topic={dsl.topic} | model={model or '自动降级'}")
        yield {"event": "runtime_start", "scene_type": dsl.scene_type.value, "topic": dsl.topic}
        
        async for event in runtime_engine.render_stream(dsl, query=query, model=model):
            if event["event"] == "chunk":
                html_chunks.append(event["content"])
                final_provider = event.get("provider", final_provider)
            elif event["event"] == "all_failed":
                yield {"event": "error", "stage": "runtime", "message": event.get("error", "所有AI模型均不可用")}
                return
            yield event
        
        # 后处理 + 保存
        logger.info(f"[HTML生成流] 后处理开始 | raw_html_len={len(''.join(html_chunks))}")
        yield {"event": "postprocess_start", "message": "正在处理生成结果..."}
        
        raw_html = "".join(html_chunks)
        
        # DEBUG: 记录 AI 返回的完整 HTML 内容
        logger.debug(f"[HTML生成流] AI返回的HTML原文:\n{raw_html}")
        
        clean_html = html_extractor.extract_html(raw_html)
        final_html = post_processor.process(clean_html)
        
        logger.info(f"[HTML生成流] HTML后处理完成 | raw_len={len(raw_html)} | clean_len={len(clean_html)} | final_len={len(final_html)}")
        
        result_id = file_store.save_html(
            html_content=final_html,
            query=query,
            dsl=dsl.model_dump(),
            provider=final_provider
        )
        
        logger.info(f"[HTML生成流] 结果保存完成 | result_id={result_id} | html_length={len(final_html)} | provider={final_provider}")
        
        yield {
            "event": "complete",
            "result_id": result_id,
            "html_url": f"/outputs/{result_id}.html",
            "provider": final_provider,
            "html_length": len(final_html)
        }


orchestrator = Orchestrator()
