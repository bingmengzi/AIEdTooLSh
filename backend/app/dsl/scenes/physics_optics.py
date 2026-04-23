"""物理光学场景特定配置"""
# 该场景的特定参数、约束等
# 随着项目迭代逐步丰富

SCENE_CONFIG = {
    "name": "physics_optics",
    "description": "物理光学场景，包括透镜成像、光的折射反射等",
    "typical_parameters": [
        {"name": "焦距f", "type": "number", "min": 1, "max": 20, "unit": "cm"},
        {"name": "物距u", "type": "number", "min": 1, "max": 50, "unit": "cm"},
        {"name": "物高h", "type": "number", "min": 0.5, "max": 5, "unit": "cm"},
        {"name": "入射角", "type": "number", "min": 0, "max": 90, "unit": "度"},
    ],
    "typical_elements": [
        "凸透镜", "凹透镜", "光屏", "蜡烛/物体",
        "光线", "主光轴", "焦点", "光心",
        "实像", "虚像", "放大镜效果",
        "反射镜", "棱镜", "光谱",
    ],
    "interaction_patterns": [
        "拖动物体调整物距", "滑块调节焦距",
        "观察成像变化", "数据记录表格",
        "显示/隐藏光线", "切换透镜类型",
    ],
    "color_scheme": {
        "light_ray": "#FFD700",       # 金色 - 光线
        "lens": "#87CEEB",            # 天蓝色 - 透镜
        "object": "#FF6347",          # 番茄红 - 物体
        "image_real": "#32CD32",      # 绿色 - 实像
        "image_virtual": "#9370DB",   # 紫色 - 虚像(虚线)
        "axis": "#333333",            # 深灰 - 光轴
    },
    "physics_rules": {
        "lens_formula": "1/f = 1/u + 1/v",
        "magnification": "m = v/u = h'/h",
        "sign_convention": "实物/实像为正，虚物/虚像为负",
    },
}
