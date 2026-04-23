"""DSL 结构校验器"""
import json
import logging
from app.dsl.schema import SceneDSL

logger = logging.getLogger(__name__)


class DSLValidator:
    """校验AI生成的DSL是否符合规范"""
    
    def validate_and_parse(self, raw_text: str) -> tuple[SceneDSL | None, list[str]]:
        """从AI输出文本中提取并校验DSL
        
        Args:
            raw_text: AI返回的原始文本（可能包含markdown代码块）
            
        Returns:
            (SceneDSL实例或None, 错误列表)
        """
        logger.info(f"[DSLValidator] 开始校验 | 输入文本长度={len(raw_text)}")
        errors = []
        
        # 提取JSON内容
        json_str = self._extract_json(raw_text)
        if not json_str:
            logger.warning("[DSLValidator] JSON提取失败 | 未找到有效的JSON内容")
            errors.append("未找到有效的JSON内容")
            return None, errors
        
        logger.info(f"[DSLValidator] JSON提取成功 | JSON长度={len(json_str)}")
        
        # 解析JSON
        try:
            data = json.loads(json_str)
            logger.debug(f"[DSLValidator] JSON解析成功 | keys={list(data.keys())}")
        except json.JSONDecodeError as e:
            logger.warning(f"[DSLValidator] JSON解析失败 | error={e}")
            errors.append(f"JSON解析失败: {e}")
            return None, errors
        
        # Pydantic校验
        try:
            dsl = SceneDSL(**data)
            logger.info(f"[DSLValidator] DSL校验成功 | topic={dsl.topic} | scene_type={dsl.scene_type.value}")
            return dsl, []
        except Exception as e:
            logger.warning(f"[DSLValidator] DSL结构校验失败 | error={e}")
            errors.append(f"DSL结构校验失败: {e}")
            return None, errors
    
    def _extract_json(self, text: str) -> str | None:
        """从文本中提取JSON"""
        import re
        
        # 尝试从 ```json ... ``` 代码块提取
        pattern = r'```json\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # 尝试从 ``` ... ``` 代码块提取
        pattern2 = r'```\s*\n(.*?)```'
        matches2 = re.findall(pattern2, text, re.DOTALL)
        for m in matches2:
            m = m.strip()
            if m.startswith('{'):
                return m
        
        # 尝试直接查找JSON对象
        text = text.strip()
        if text.startswith('{'):
            # 找到最外层的花括号对
            depth = 0
            for i, c in enumerate(text):
                if c == '{': depth += 1
                elif c == '}': depth -= 1
                if depth == 0:
                    return text[:i+1]
        
        return None
    
    def create_fallback_dsl(self, subject: str, branch: str, topic: str, scene_type: str) -> SceneDSL:
        """当AI生成的DSL校验失败时，创建一个合理的默认DSL"""
        from app.dsl.schema import (SubjectType, SceneType, LayoutType, 
                                      TechStack, InteractionConfig, AnimationConfig)
        
        # 根据场景类型确定技术栈和交互方式
        tech = TechStack(tailwind=True, fontawesome=True)
        interactions = InteractionConfig()
        layout = LayoutType.LEFT_CANVAS_RIGHT_PANEL
        
        if scene_type == "canvas_interactive":
            tech.canvas_2d = True
            interactions.draggable = True
            interactions.sliders = True
        elif scene_type == "threejs_3d":
            tech.threejs = True
            tech.mathjax = True
            layout = LayoutType.SPLIT_3D_STEPS
            interactions.step_buttons = True
        elif scene_type == "step_derivation":
            tech.mathjax = True
            interactions.step_buttons = True
            layout = LayoutType.FULL_CANVAS
        elif scene_type == "hybrid":
            tech.threejs = True
            tech.mathjax = True
            interactions.step_buttons = True
            layout = LayoutType.SPLIT_3D_STEPS
        
        return SceneDSL(
            subject=SubjectType(subject) if subject in SubjectType._value2member_map_ else SubjectType.MATH,
            branch=branch,
            topic=topic,
            description=f"关于{topic}的交互教学场景",
            scene_type=SceneType(scene_type) if scene_type in SceneType._value2member_map_ else SceneType.CANVAS_INTERACTIVE,
            layout=layout,
            tech_stack=tech,
            interactions=interactions,
            animations=AnimationConfig(has_animation=True, animation_type="interactive"),
            key_concepts=[topic],
            visual_elements=[],
            parameters=[],
            learning_objectives=[f"理解和掌握{topic}的核心概念"]
        )


dsl_validator = DSLValidator()
