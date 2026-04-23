"""场景DSL基类 - 定义场景通用结构"""

# 场景类型到默认配置的映射
SCENE_DEFAULTS = {
    "canvas_interactive": {
        "description": "2D Canvas交互场景，适合几何、函数图像、物理模拟",
        "tech_requirements": ["canvas_2d", "tailwind", "fontawesome"],
        "default_layout": "left_canvas_right_panel",
        "interaction_types": ["drag", "slider", "animation"],
        "reference_examples": ["勾股定理", "将军饮马问题", "凸透镜成像"],
    },
    "threejs_3d": {
        "description": "Three.js 3D场景，适合立体几何、空间向量、分子结构",
        "tech_requirements": ["threejs", "tailwind", "fontawesome"],
        "default_layout": "split_3d_steps",
        "interaction_types": ["orbit", "click", "step"],
        "reference_examples": ["几何体解题", "四面体数学题"],
    },
    "step_derivation": {
        "description": "步骤推导场景，适合证明题、推导题",
        "tech_requirements": ["mathjax", "tailwind", "fontawesome"],
        "default_layout": "full_canvas",
        "interaction_types": ["step", "click"],
        "reference_examples": [],
    },
    "hybrid": {
        "description": "混合场景，3D+步骤推导组合",
        "tech_requirements": ["threejs", "mathjax", "tailwind", "fontawesome"],
        "default_layout": "split_3d_steps",
        "interaction_types": ["orbit", "step", "click"],
        "reference_examples": ["几何体解题"],
    },
}


def get_scene_defaults(scene_type: str) -> dict:
    """获取场景类型的默认配置"""
    return SCENE_DEFAULTS.get(scene_type, SCENE_DEFAULTS["canvas_interactive"])
