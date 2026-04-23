"""物理力学场景特定配置"""
# 该场景的特定参数、约束等
# 随着项目迭代逐步丰富

SCENE_CONFIG = {
    "name": "physics_mechanics",
    "description": "物理力学场景，包括受力分析、运动模拟、能量守恒等",
    "typical_parameters": [
        {"name": "质量m", "type": "number", "min": 0.1, "max": 100, "unit": "kg"},
        {"name": "力F", "type": "number", "min": 0, "max": 1000, "unit": "N"},
        {"name": "角度θ", "type": "number", "min": 0, "max": 90, "unit": "度"},
        {"name": "摩擦系数μ", "type": "number", "min": 0, "max": 1},
        {"name": "初速度v₀", "type": "number", "min": 0, "max": 50, "unit": "m/s"},
        {"name": "加速度a", "type": "number", "min": -10, "max": 10, "unit": "m/s²"},
    ],
    "typical_elements": [
        "物体/质点", "力的箭头", "速度矢量",
        "斜面", "滑轮", "弹簧", "绳子",
        "轨迹曲线", "坐标系", "参考系",
        "能量柱状图", "速度-时间图",
    ],
    "interaction_patterns": [
        "拖动调整角度", "滑块改变参数",
        "播放/暂停动画", "调节时间速度",
        "显示/隐藏力的分解", "切换参考系",
    ],
    "color_scheme": {
        "gravity": "#8B4513",         # 棕色 - 重力
        "normal_force": "#4169E1",    # 蓝色 - 支持力
        "friction": "#FF8C00",        # 橙色 - 摩擦力
        "applied_force": "#DC143C",   # 红色 - 外力
        "velocity": "#228B22",        # 绿色 - 速度
        "acceleration": "#9400D3",    # 紫色 - 加速度
    },
    "physics_rules": {
        "newtons_second_law": "F = ma",
        "kinematic_equations": [
            "v = v₀ + at",
            "x = v₀t + ½at²",
            "v² = v₀² + 2ax",
        ],
        "energy_conservation": "E_k + E_p = 常量",
    },
}
