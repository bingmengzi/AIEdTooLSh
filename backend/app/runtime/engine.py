"""Runtime Engine - DSL到HTML的核心引擎"""
import json
import logging
from typing import AsyncGenerator
from pathlib import Path

from app.dsl.schema import SceneDSL
from app.prompts.manager import prompt_manager
from app.prompts.example_manager import example_manager
from app.providers import fallback_manager
from app.config import settings

logger = logging.getLogger(__name__)


class RuntimeEngine:
    """运行时引擎：将 SceneDSL 转化为可交互 HTML"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
    
    def _load_template(self, template_name: str) -> str:
        """加载Runtime模板"""
        file_path = self.templates_dir / template_name
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8").strip()
            logger.info(f"加载Runtime模板: {template_name} | 长度={len(content)}")
            return content
        logger.warning(f"Runtime模板不存在: {template_name}")
        return ""
    
    def _get_template_for_scene(self, scene_type: str) -> str:
        """根据场景类型选择模板"""
        mapping = {
            "canvas_interactive": "canvas2d_template.txt",
            "threejs_3d": "threejs_template.txt",
            "step_derivation": "base_template.txt",
            "hybrid": "threejs_template.txt",
        }
        template_name = mapping.get(scene_type, "base_template.txt")
        return self._load_template(template_name)
    
    def build_generation_prompt(self, dsl: SceneDSL, query: str = "") -> list[dict]:
        """构建最终的HTML生成提示词
        
        组装顺序：
        1. 系统角色 (base_role.txt)
        2. 学科提示词 (subjects/math/geometry.txt 等)
        3. 场景类型提示词 (scenes/canvas_interactive.txt 等)
        4. 质量约束 (quality/*.txt)
        5. Runtime模板 (作为参考架构)
        6. 参考案例（智能匹配1-2个）
        7. DSL描述 (用户输入转化后的结构化需求)
        
        Args:
            dsl: 场景DSL对象
            query: 用户原始查询文本，用于参考案例关键词匹配
        """
        logger.info(f"[RuntimeEngine] 开始构建生成提示词 | topic={dsl.topic} | scene_type={dsl.scene_type.value} | query_len={len(query)}")
        
        # 获取多级提示词
        messages = prompt_manager.assemble_prompt(
            subject=dsl.subject.value,
            branch=dsl.branch,
            scene_type=dsl.scene_type.value,
            user_input=""  # user_input 将单独构建
        )
        
        # 获取Runtime模板
        runtime_template = self._get_template_for_scene(dsl.scene_type.value)
        
        # 构建用户消息：DSL + Runtime模板 + 具体要求
        user_content_parts = []
        
        # DSL描述
        user_content_parts.append("## 场景需求描述 (Scene DSL)")
        user_content_parts.append(f"```json\n{dsl.model_dump_json(indent=2)}\n```")
        
        # Runtime模板参考
        if runtime_template:
            user_content_parts.append("\n## 参考架构模板")
            user_content_parts.append(runtime_template)
            logger.info(f"[RuntimeEngine] 注入Runtime模板 | 长度={len(runtime_template)}")
        
        # 获取并注入参考案例（智能匹配1-2个）
        examples = example_manager.get_examples(
            scene_type=dsl.scene_type.value,
            subject=dsl.subject.value,
            branch=dsl.branch,
            query=query
        )
        
        if examples:
            user_content_parts.append("\n## 参考案例")
            user_content_parts.append("以下是高质量教育交互动画的完整HTML参考代码。你的输出必须达到同等质量水平，模仿其代码结构、交互设计、视觉风格和教育呈现方式。")
            
            # Token 预算控制
            MAX_TOTAL_EXAMPLE_CHARS = 150000  # 约 50K tokens
            total_chars = 0
            
            for i, (content, source, desc) in enumerate(examples):
                label = "主要参考" if i == 0 else "补充参考"
                
                # Token 预算控制：第2个参考如果超预算，只注入关键部分（前60%）
                if i == 1 and total_chars + len(content) > MAX_TOTAL_EXAMPLE_CHARS:
                    truncate_len = int(len(content) * 0.6)
                    content = content[:truncate_len] + "\n<!-- ... 参考代码已截断，请参考主要参考的完整结构 ... -->"
                    logger.info(f"[RuntimeEngine] 补充参考超预算，截断至 {truncate_len} 字符")
                
                user_content_parts.append(f"\n### {label}（{desc}）")
                user_content_parts.append(f"<!-- 来源: {source} -->")
                user_content_parts.append(content)
                
                total_chars += len(content)
                logger.info(f"[RuntimeEngine] 注入参考案例 [{i+1}] | source={source} | 长度={len(content)} | desc={desc}")
            
            user_content_parts.append("\n请严格模仿上述参考案例的代码质量、布局结构、交互设计和视觉风格。")
        else:
            logger.info(f"[RuntimeEngine] 未找到参考案例 | scene_type={dsl.scene_type.value} | subject={dsl.subject.value} | branch={dsl.branch}")
        
        # 具体生成指令
        user_content_parts.append(f"\n## 生成要求")
        user_content_parts.append(f"请根据以上 Scene DSL 描述，生成一个关于「{dsl.topic}」的完整可交互教学HTML页面。")
        user_content_parts.append("要求：")
        user_content_parts.append(f"1. 主题: {dsl.topic}")
        if dsl.description:
            user_content_parts.append(f"2. 场景描述: {dsl.description}")
        if dsl.key_concepts:
            user_content_parts.append(f"3. 核心概念: {', '.join(dsl.key_concepts)}")
        if dsl.visual_elements:
            user_content_parts.append(f"4. 视觉元素: {', '.join(dsl.visual_elements)}")
        if dsl.parameters:
            params_desc = [f"{p.get('name','参数')}(范围{p.get('min',0)}-{p.get('max',10)}, 默认{p.get('default',5)})" for p in dsl.parameters]
            user_content_parts.append(f"5. 可调参数: {', '.join(params_desc)}")
        if dsl.learning_objectives:
            user_content_parts.append(f"6. 学习目标: {', '.join(dsl.learning_objectives)}")
        
        user_content_parts.append("\n请直接输出完整的HTML代码，用```html和```包裹。不要输出任何解释文字。")
        
        # 替换或追加user消息
        user_content = "\n".join(user_content_parts)
        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"] = user_content
        else:
            messages.append({"role": "user", "content": user_content})
        
        # 日志：记录最终 prompt 长度
        system_len = sum(len(m["content"]) for m in messages if m["role"] == "system")
        user_len = sum(len(m["content"]) for m in messages if m["role"] == "user")
        logger.info(f"[RuntimeEngine] 提示词构建完成 | system_chars={system_len} | user_chars={user_len} | total={system_len + user_len}")
        
        # DEBUG: 记录完整的 prompt 内容
        for msg in messages:
            if msg["role"] == "system":
                logger.debug(f"[RuntimeEngine] HTML生成 System Prompt 全文:\n{msg['content']}")
            elif msg["role"] == "user":
                logger.debug(f"[RuntimeEngine] HTML生成 User Prompt 全文:\n{msg['content']}")
        
        return messages
    
    async def render_stream(
        self, 
        dsl: SceneDSL,
        query: str = "",
        temperature: float = 0.7,
        max_tokens: int = 16384,
        model: str = ""
    ) -> AsyncGenerator[dict, None]:
        """流式生成HTML
        
        Args:
            dsl: 场景DSL对象
            query: 用户原始查询文本，用于参考案例关键词匹配
            temperature: 生成温度
            max_tokens: 最大token数
            model: 指定模型名称，空则自动降级
        
        Yields:
            dict: 事件对象
            - {"event": "render_start", "scene_type": "...", "template": "..."}
            - {"event": "provider_start", "provider": "kimi", "model": "..."}
            - {"event": "chunk", "provider": "kimi", "content": "..."}
            - {"event": "fallback", "from": "kimi", "to": "qwen"}
            - {"event": "render_done", "provider": "kimi"}
            - {"event": "render_error", "error": "..."}
        """
        template_name = {
            "canvas_interactive": "canvas2d_template.txt",
            "threejs_3d": "threejs_template.txt",
            "step_derivation": "base_template.txt",
            "hybrid": "threejs_template.txt",
        }.get(dsl.scene_type.value, "base_template.txt")
        
        logger.info(f"[RuntimeEngine] render_stream 开始 | scene_type={dsl.scene_type.value} | template={template_name} | model={model or '自动降级'} | query_len={len(query)}")
        
        yield {
            "event": "render_start",
            "scene_type": dsl.scene_type.value,
            "template": template_name,
            "topic": dsl.topic
        }
        
        # 构建prompt（传入query用于智能匹配参考案例）
        messages = self.build_generation_prompt(dsl, query=query)
        
        # 获取参考案例信息（用于前端展示）
        examples = example_manager.get_examples(
            scene_type=dsl.scene_type.value,
            subject=dsl.subject.value,
            branch=dsl.branch,
            query=query
        )
        example_sources = [src for _, src, _ in examples] if examples else []
        
        # 记录prompt信息（用于前端展示）
        system_prompt_preview = ""
        user_prompt_preview = ""
        full_system_prompt = ""
        full_user_prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                full_system_prompt = msg["content"]
                system_prompt_preview = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
            elif msg["role"] == "user":
                full_user_prompt = msg["content"]
                user_prompt_preview = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
        
        yield {
            "event": "prompt_built",
            "system_prompt_preview": system_prompt_preview,
            "user_prompt_preview": user_prompt_preview,
            "full_system_prompt": full_system_prompt,  # 新增：完整 system prompt
            "full_user_prompt": full_user_prompt,      # 新增：完整 user prompt
            "total_system_length": sum(len(m["content"]) for m in messages if m["role"] == "system"),
            "total_user_length": sum(len(m["content"]) for m in messages if m["role"] == "user"),
            "has_example": bool(examples),
            "example_sources": example_sources,  # 改为列表，支持多参考案例
        }
        
        # 调用AI生成（根据 model 参数选择调用方式）
        try:
            logger.info(f"[RuntimeEngine] 开始调用AI生成 | model={model or '自动降级'}")
            if model:
                # 使用指定模型（不降级）
                stream = fallback_manager.chat_stream_single(
                    provider_name=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            else:
                # 自动降级
                stream = fallback_manager.chat_stream_with_fallback(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            
            async for event in stream:
                yield event
        except Exception as e:
            logger.error(f"Runtime渲染失败: {e}")
            yield {"event": "render_error", "error": str(e)}


runtime_engine = RuntimeEngine()
