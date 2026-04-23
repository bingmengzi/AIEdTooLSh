"""学科识别与场景类型判定服务"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# 关键词库定义
SUBJECT_KEYWORDS = {
    "math": {
        "geometry": [
            "三角形", "圆", "正方形", "矩形", "多边形", "勾股", "几何",
            "角度", "面积", "周长", "对称", "全等", "相似", "坐标",
            "向量", "平行", "垂直", "切线", "弦", "内接", "外接",
            "棱锥", "棱柱", "四面体", "正方体", "长方体", "空间",
            "二面角", "截面", "展开图", "旋转体", "三棱锥", "圆锥",
            "正三角形", "等边", "等腰", "直角", "钝角", "锐角",
            "中点", "垂心", "外心", "内心", "重心", "旁心",
            "三视图", "正交投影", "立体", "平面", "异面直线",
            "饮马问题", "将军饮马", "最短路径"
        ],
        "algebra": [
            "方程", "函数", "不等式", "数列", "求和", "极限",
            "导数", "积分", "微分", "多项式", "因式分解",
            "一次", "二次", "指数", "对数", "三角函数",
            "抛物线", "双曲线", "椭圆", "圆锥曲线",
            "等差", "等比", "递推", "通项", "前n项和",
            "单调性", "最值", "零点", "定义域", "值域",
            # 解析几何/坐标系相关
            "焦点", "准线", "顶点", "开口方向", "对称轴",
            "函数图像", "二次函数", "坐标轴", "坐标系",
            "离心率", "长轴", "短轴", "渐近线", "标准方程",
            "参数方程", "极坐标", "直角坐标"
        ],
        "general": [
            "概率", "统计", "排列", "组合", "集合", "逻辑",
            "证明", "定理", "公式", "计算", "解方程"
        ]
    },
    "physics": {
        "optics": [
            "透镜", "凸透镜", "凹透镜", "光线", "折射", "反射",
            "成像", "焦距", "光学焦点", "物距", "像距", "光路",
            "棱镜", "光谱", "色散", "衍射", "干涉", "偏振",
            "全反射", "临界角", "光的本质", "光速",
            "实像", "虚像", "放大镜", "望远镜", "显微镜"
        ],
        "mechanics": [
            "力", "牛顿", "加速度", "速度", "位移", "重力",
            "摩擦力", "弹力", "动量", "能量", "功", "功率",
            "杠杆", "滑轮", "斜面", "弹簧", "碰撞",
            "抛体", "圆周运动", "万有引力", "简谐运动",
            "动能", "势能", "机械能", "守恒", "冲量",
            "平衡", "受力分析", "合力", "分力"
        ],
        "electricity": [
            "电路", "电流", "电压", "电阻", "欧姆",
            "串联", "并联", "电功", "电功率", "电磁",
            "电场", "磁场", "电磁感应", "楞次定律",
            "电容", "电感", "交流电", "变压器"
        ],
        "general": [
            "运动", "波动", "振动", "热学", "温度",
            "热量", "内能", "比热容", "热传递"
        ]
    },
    "chemistry": {
        "general": [
            "元素", "原子", "分子", "化合物", "化学反应",
            "酸", "碱", "盐", "氧化", "还原", "离子",
            "化学键", "共价键", "离子键", "周期表",
            "摩尔", "浓度", "溶液", "沉淀", "催化",
            "燃烧", "置换", "复分解", "化合", "分解",
            "电解", "电离", "水解", "中和", "滴定"
        ]
    }
}

# 场景类型判定规则
SCENE_TYPE_RULES = {
    # 3D场景关键词
    "threejs_3d": [
        "棱锥", "棱柱", "四面体", "正方体", "长方体",
        "空间", "二面角", "截面", "三棱锥", "圆锥",
        "分子结构", "晶体", "立体", "三视图",
        "外接球", "内切球", "异面直线", "空间向量"
    ],
    # 步骤推导场景关键词
    "step_derivation": [
        "证明", "推导", "求解过程", "解题步骤",
        "证", "求证", "论证"
    ],
}


class SubjectAnalyzer:
    """学科分析器 - 分析用户输入，识别学科和场景类型"""

    def analyze(self, query: str) -> dict:
        """分析用户输入的题目/概念

        Args:
            query: 用户输入的文本

        Returns:
            {
                "subject": "math",           # 学科
                "branch": "geometry",         # 分支
                "scene_type": "canvas_interactive",  # 场景类型
                "confidence": 0.85,           # 置信度
                "keywords_matched": ["三角形", "勾股"]  # 匹配的关键词
            }
        """
        query_clean = query.strip()

        # 统计各学科各分支的匹配数
        scores = {}
        matched_keywords = []

        for subject, branches in SUBJECT_KEYWORDS.items():
            for branch, keywords in branches.items():
                count = 0
                for kw in keywords:
                    if kw in query_clean:
                        count += 1
                        if kw not in matched_keywords:
                            matched_keywords.append(kw)
                if count > 0:
                    key = f"{subject}/{branch}"
                    scores[key] = count

        if not scores:
            # 没有匹配到任何关键词，默认为数学/通用
            logger.info(f"未匹配到关键词，默认使用 math/general: {query[:50]}...")
            return {
                "subject": "math",
                "branch": "general",
                "scene_type": "canvas_interactive",
                "confidence": 0.3,
                "keywords_matched": []
            }

        # 找到得分最高的学科/分支
        best_key = max(scores, key=scores.get)
        subject, branch = best_key.split("/")
        total_keywords = sum(scores.values())
        confidence = min(0.95, 0.5 + total_keywords * 0.1)

        # 判定场景类型
        scene_type = self._determine_scene_type(query_clean, subject, branch)

        result = {
            "subject": subject,
            "branch": branch,
            "scene_type": scene_type,
            "confidence": round(confidence, 2),
            "keywords_matched": matched_keywords
        }

        logger.info(f"学科分析结果: subject={subject}, branch={branch}, "
                    f"scene={scene_type}, confidence={confidence:.2f}, "
                    f"keywords={matched_keywords[:5]}")
        return result

    def _determine_scene_type(self, query: str, subject: str, branch: str) -> str:
        """判定场景类型"""
        is_3d = any(kw in query for kw in SCENE_TYPE_RULES["threejs_3d"])
        is_derivation = any(kw in query for kw in SCENE_TYPE_RULES["step_derivation"])

        # 混合场景（3D + 推导）
        if is_3d and is_derivation:
            return "hybrid"
        # 纯3D场景
        elif is_3d:
            return "threejs_3d"
        # 纯推导场景
        elif is_derivation:
            return "step_derivation"
        # 默认为Canvas 2D交互场景
        else:
            return "canvas_interactive"

    def get_prompt_params(self, query: str) -> dict:
        """获取用于提示词组装的参数

        这是一个便捷方法，返回可直接传给 PromptManager.assemble_prompt() 的参数

        Returns:
            {
                "subject": "math",
                "branch": "geometry",
                "scene_type": "canvas_interactive",
                "user_input": "原始查询"
            }
        """
        analysis = self.analyze(query)
        return {
            "subject": analysis["subject"],
            "branch": analysis["branch"],
            "scene_type": analysis["scene_type"],
            "user_input": query
        }


# 全局单例
subject_analyzer = SubjectAnalyzer()
