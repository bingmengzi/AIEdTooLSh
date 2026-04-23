"""3D立体几何场景特定配置"""
# 该场景的特定参数、约束等
# 随着项目迭代逐步丰富

SCENE_CONFIG = {
    "name": "geometry_3d",
    "description": "3D立体几何场景，包括棱锥、棱柱、球体等空间几何体",
    "typical_parameters": [
        {"name": "底面边长", "type": "number", "min": 1, "max": 10},
        {"name": "高度", "type": "number", "min": 1, "max": 10},
        {"name": "二面角", "type": "number", "min": 0, "max": 180},
    ],
    "typical_elements": [
        "三棱锥", "四面体", "正方体", "长方体",
        "棱柱", "圆锥", "圆柱", "球体",
        "截面", "展开图", "辅助线",
        "坐标轴", "平面", "法向量",
    ],
    "interaction_patterns": [
        "轨道控制(旋转/缩放)", "点击选择顶点",
        "显示/隐藏辅助元素", "视角切换",
        "步骤推导", "动画演示",
    ],
    "camera_presets": {
        "front": {"position": [0, -10, 5], "target": [0, 0, 0]},
        "top": {"position": [0, 0, 15], "target": [0, 0, 0]},
        "iso": {"position": [8, -8, 8], "target": [0, 0, 0]},
    },
    "material_settings": {
        "face_opacity": 0.3,
        "edge_color": "#1E3A5F",
        "vertex_color": "#FF6B6B",
    },
}
