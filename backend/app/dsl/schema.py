"""Scene DSL Schema - 场景描述语言模型定义"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SubjectType(str, Enum):
    MATH = "math"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"


class SceneType(str, Enum):
    CANVAS_INTERACTIVE = "canvas_interactive"
    THREEJS_3D = "threejs_3d"
    STEP_DERIVATION = "step_derivation"
    HYBRID = "hybrid"


class LayoutType(str, Enum):
    LEFT_CANVAS_RIGHT_PANEL = "left_canvas_right_panel"
    LEFT_PANEL_RIGHT_CANVAS = "left_panel_right_canvas"
    FULL_CANVAS = "full_canvas"
    SPLIT_3D_STEPS = "split_3d_steps"


class TechStack(BaseModel):
    """技术栈配置"""
    canvas_2d: bool = False
    threejs: bool = False
    mathjax: bool = False
    tailwind: bool = True
    fontawesome: bool = True


class InteractionConfig(BaseModel):
    """交互配置"""
    draggable: bool = False          # 支持拖拽
    sliders: bool = False            # 支持滑块控制
    step_buttons: bool = False       # 步骤按钮
    animation_controls: bool = False # 动画控制(播放/暂停/速度)
    data_recording: bool = False     # 数据记录表格
    theme_switch: bool = False       # 主题切换


class AnimationConfig(BaseModel):
    """动画配置"""
    has_animation: bool = False
    animation_type: str = ""    # "continuous" | "step" | "interactive"
    description: str = ""


class SceneDSL(BaseModel):
    """场景描述语言 - AI阶段1输出的结构化描述"""
    
    # 基本信息
    subject: SubjectType = Field(description="学科类型")
    branch: str = Field(default="general", description="学科分支，如geometry/optics")
    topic: str = Field(description="主题名称，如'勾股定理'")
    description: str = Field(default="", description="场景描述")
    
    # 场景配置
    scene_type: SceneType = Field(description="场景类型")
    layout: LayoutType = Field(default=LayoutType.LEFT_CANVAS_RIGHT_PANEL)
    
    # 技术配置
    tech_stack: TechStack = Field(default_factory=TechStack)
    interactions: InteractionConfig = Field(default_factory=InteractionConfig)
    animations: AnimationConfig = Field(default_factory=AnimationConfig)
    
    # 内容要素
    key_concepts: list[str] = Field(default_factory=list, description="核心概念/公式")
    visual_elements: list[str] = Field(default_factory=list, description="需要绘制的视觉元素")
    parameters: list[dict] = Field(default_factory=list, description="可调参数列表，如[{'name':'边长a','min':1,'max':10,'default':3}]")
    
    # 教学目标
    learning_objectives: list[str] = Field(default_factory=list, description="学习目标")
    
    class Config:
        json_schema_extra = {
            "example": {
                "subject": "math",
                "branch": "geometry",
                "topic": "勾股定理",
                "description": "展示直角三角形三边关系 a²+b²=c²",
                "scene_type": "canvas_interactive",
                "layout": "left_canvas_right_panel",
                "tech_stack": {"canvas_2d": True, "tailwind": True, "fontawesome": True},
                "interactions": {"draggable": True, "sliders": True},
                "key_concepts": ["a² + b² = c²", "直角三角形"],
                "visual_elements": ["直角三角形", "三条边的正方形", "面积标注"],
                "parameters": [
                    {"name": "底边a", "min": 2, "max": 10, "default": 3},
                    {"name": "高b", "min": 2, "max": 10, "default": 4}
                ]
            }
        }
