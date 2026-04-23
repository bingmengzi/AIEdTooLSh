"""2D几何场景特定配置"""
# 该场景的特定参数、约束等
# 随着项目迭代逐步丰富

SCENE_CONFIG = {
    "name": "geometry_2d",
    "description": "2D平面几何场景，包括三角形、圆、多边形等",
    "typical_parameters": [
        {"name": "边长", "type": "number", "min": 1, "max": 20},
        {"name": "角度", "type": "number", "min": 0, "max": 180},
        {"name": "半径", "type": "number", "min": 1, "max": 15},
    ],
    "typical_elements": [
        "三角形", "圆", "正方形", "矩形", "多边形",
        "角度标注", "长度标注", "面积标注",
        "辅助线", "坐标轴", "网格线",
    ],
    "interaction_patterns": [
        "拖拽顶点", "滑块调参", "点击高亮",
        "动画演示", "步骤展示",
    ],
    "color_scheme": {
        "primary": "#3B82F6",      # 蓝色 - 主要图形
        "secondary": "#10B981",    # 绿色 - 辅助元素
        "accent": "#F59E0B",       # 橙色 - 强调元素
        "background": "#F8FAFC",   # 浅灰 - 背景
    },
}
