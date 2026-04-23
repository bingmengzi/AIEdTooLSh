"""参考案例管理器 - 管理和注入 Few-Shot 代码示例（智能匹配版）"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ExampleManager:
    """多参考案例智能匹配管理器"""
    
    # 定义参考案例注册表
    REFERENCE_REGISTRY = [
        {
            "id": "canvas_basic",
            "file": "canvas_interactive/ref_canvas_basic.txt",
            "tech": "canvas_2d",
            "subjects": ["math"],
            "branches": ["geometry", "algebra", "coordinate"],
            "interactions": ["draggable", "sliders", "calculation"],
            "complexity": "basic",
            "keywords": ["勾股", "三角形", "正方形", "面积", "直角", "坐标", "点", "线段"],
            "description": "Canvas基础范式：拖拽+滑块+实时计算"
        },
        {
            "id": "canvas_advanced",
            "file": "canvas_interactive/ref_canvas_advanced.txt",
            "tech": "canvas_2d",
            "subjects": ["math"],
            "branches": ["trigonometry", "function", "circle"],
            "interactions": ["draggable", "animation", "auto_demo"],
            "complexity": "advanced",
            "keywords": ["三角函数", "sin", "cos", "tan", "单位圆", "波形", "周期", "振幅", "角度"],
            "description": "Canvas高级范式：状态机管理+多图层渲染+自动演示"
        },
        {
            "id": "complex_interactive",
            "file": "canvas_interactive/ref_complex_interactive.txt",
            "tech": "canvas_2d",
            "subjects": ["physics", "math"],
            "branches": ["optics", "mechanics", "geometry"],
            "interactions": ["sliders", "tabs", "theme_switch", "animation", "data_record"],
            "complexity": "advanced",
            "keywords": ["透镜", "成像", "焦距", "光线", "物理", "实验", "折射", "反射", "记录", "分析"],
            "description": "复杂交互范式：多TAB面板+主题切换+物理模型+数据记录"
        },
        {
            "id": "threejs_3d",
            "file": "threejs_3d/ref_threejs_3d.txt",
            "tech": "threejs",
            "subjects": ["math"],
            "branches": ["solid_geometry", "proof", "3d"],
            "interactions": ["3d_rotation", "step_derivation", "highlight"],
            "complexity": "advanced",
            "keywords": ["四面体", "棱锥", "棱柱", "立方体", "空间", "三维", "体积", "表面积", "截面", "证明", "垂直", "棱"],
            "description": "Three.js 3D范式：3D几何+MathJax公式+步骤推导"
        },
        {
            "id": "svg_animation",
            "file": "svg_animation/ref_svg_animation.txt",
            "tech": "svg",
            "subjects": ["math"],
            "branches": ["solid_geometry", "proof", "derivation"],
            "interactions": ["animation", "quiz", "step_derivation"],
            "complexity": "advanced",
            "keywords": ["圆锥", "圆柱", "推导", "闯关", "练习", "体积", "公式推导", "证明"],
            "description": "SVG动画范式：步骤动画+闯关练习+公式推导"
        },
        {
            "id": "parabola_reference",
            "file": "canvas_interactive/reference_full.txt",
            "tech": "canvas_2d",
            "subjects": ["math"],
            "branches": ["curve", "conic", "function", "algebra"],
            "interactions": ["draggable", "sliders", "animation", "trace"],
            "complexity": "advanced",
            "keywords": ["抛物线", "焦点", "准线", "圆锥曲线", "椭圆", "双曲线", "方程", "函数图像", "曲线"],
            "description": "Canvas曲线范式：参数方程+拖拽+轨迹演示"
        }
    ]
    
    # 技术栈映射
    TECH_MAP = {
        "canvas_interactive": "canvas_2d",
        "threejs_3d": "threejs",
        "step_derivation": "svg",  # 步骤推导优先SVG/HTML
        "hybrid": "canvas_2d"  # 混合默认Canvas
    }
    
    def __init__(self):
        self.examples_dir = Path(__file__).parent / "examples"
        self.examples_dir.mkdir(parents=True, exist_ok=True)
    
    def get_examples(self, scene_type: str, subject: str = "", branch: str = "", query: str = "") -> list[tuple[str, str, str]]:
        """智能匹配参考案例，返回1-2个最相关的参考
        
        Args:
            scene_type: 场景类型 (canvas_interactive, threejs_3d, etc.)
            subject: 学科 (math, physics, chemistry)
            branch: 分支 (geometry, algebra, optics, etc.)
            query: 用户查询文本，用于关键词匹配
        
        Returns:
            list of (content, source_path, description)
        """
        logger.info(f"[ExampleManager] 开始智能匹配 | scene_type={scene_type} | subject={subject} | branch={branch} | query_len={len(query)}")
        
        # 计算所有参考案例的得分
        scored_refs = []
        for ref in self.REFERENCE_REGISTRY:
            score = self._calculate_score(ref, scene_type, subject, branch, query)
            scored_refs.append((score, ref))
            logger.debug(f"[ExampleManager] 参考案例 {ref['id']} 得分={score:.1f}")
        
        # 按得分排序，取前2个
        scored_refs.sort(key=lambda x: x[0], reverse=True)
        
        # 筛选得分 > 0 的参考
        valid_refs = [(score, ref) for score, ref in scored_refs if score > 0]
        
        if not valid_refs:
            logger.info("[ExampleManager] 无有效匹配的参考案例")
            return []
        
        # 取前2个（如果第一个得分足够高，或者只有1个）
        results = []
        for i, (score, ref) in enumerate(valid_refs[:2]):
            # 如果第二个得分太低（不到第一个的50%），跳过
            if i == 1 and score < valid_refs[0][0] * 0.5:
                logger.debug(f"[ExampleManager] 跳过补充参考 {ref['id']}，得分过低 ({score:.1f} < {valid_refs[0][0] * 0.5:.1f})")
                break
            
            content, source = self._load_reference(ref)
            if content:
                results.append((content, source, ref["description"]))
                logger.info(f"[ExampleManager] 选中参考案例 [{i+1}] {ref['id']} | 得分={score:.1f} | 描述={ref['description']}")
        
        logger.info(f"[ExampleManager] 匹配完成，返回 {len(results)} 个参考案例")
        return results
    
    def _calculate_score(self, ref: dict, scene_type: str, subject: str, branch: str, query: str) -> float:
        """计算参考案例与当前需求的匹配得分"""
        score = 0.0
        
        # 1. 技术栈匹配（权重40%）
        target_tech = self.TECH_MAP.get(scene_type, "canvas_2d")
        if ref["tech"] == target_tech:
            score += 40
        elif target_tech == "canvas_2d" and ref["tech"] == "svg":
            # SVG 也可以作为 Canvas 的备选
            score += 20
        
        # 2. 学科匹配（权重20%）
        if subject and subject in ref["subjects"]:
            score += 20
        
        # 3. 分支匹配（权重20%）
        if branch and branch in ref["branches"]:
            score += 20
        elif branch:
            # 模糊匹配分支
            for ref_branch in ref["branches"]:
                if branch in ref_branch or ref_branch in branch:
                    score += 10
                    break
        
        # 4. 关键词匹配（权重20%）
        if query:
            matched_count = sum(1 for kw in ref["keywords"] if kw in query)
            keyword_score = min(20, matched_count * 5)  # 每个关键词5分，最多20分
            score += keyword_score
        
        return score
    
    def _load_reference(self, ref: dict) -> tuple[str, str]:
        """加载参考案例文件内容"""
        file_path = self.examples_dir / ref["file"]
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8").strip()
                if content:
                    return content, ref["file"]
            except Exception as e:
                logger.error(f"[ExampleManager] 加载参考案例失败 {ref['file']}: {e}")
        else:
            logger.warning(f"[ExampleManager] 参考案例文件不存在: {file_path}")
        return "", ""
    
    def get_example(self, scene_type: str, subject: str = "", branch: str = "") -> tuple[str, str]:
        """获取匹配的参考代码片段（向后兼容接口）
        
        查找优先级（重构后）：
        1. 智能匹配：调用 get_examples() 取第一个结果
        2. 降级匹配：按原有逻辑依次查找
        
        Args:
            scene_type: 场景类型 (canvas_interactive, threejs_3d, etc.)
            subject: 学科 (math, physics, chemistry)
            branch: 分支 (geometry, algebra, optics, etc.)
        
        Returns:
            tuple: (参考代码片段字符串, 匹配到的文件路径)
        """
        logger.info(f"[ExampleManager] get_example (兼容接口) | scene_type={scene_type} | subject={subject} | branch={branch}")
        
        # 尝试新的智能匹配
        examples = self.get_examples(scene_type, subject, branch, query="")
        if examples:
            content, source, _ = examples[0]
            return content, source
        
        # 降级到旧逻辑
        logger.info(f"[ExampleManager] 智能匹配无结果，降级到旧逻辑")
        return self._fallback_get_example(scene_type, subject, branch)
    
    def _fallback_get_example(self, scene_type: str, subject: str = "", branch: str = "") -> tuple[str, str]:
        """降级查找逻辑（保持向后兼容）"""
        candidates = []
        # 优先：完整参考案例
        candidates.append(self.examples_dir / scene_type / "reference_full.txt")
        if subject and branch:
            candidates.append(self.examples_dir / scene_type / f"{subject}_{branch}.txt")
        if subject:
            candidates.append(self.examples_dir / scene_type / f"{subject}.txt")
        candidates.append(self.examples_dir / scene_type / "_default.txt")
        candidates.append(self.examples_dir / "_common.txt")
        
        for path in candidates:
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    rel_path = str(path.relative_to(self.examples_dir))
                    logger.info(f"[ExampleManager] 降级加载成功 | 路径={rel_path}")
                    return content, rel_path
        
        return "", ""
    
    def list_examples(self) -> list[dict]:
        """列出所有可用的参考案例"""
        result = []
        for file in sorted(self.examples_dir.rglob("*.txt")):
            rel = file.relative_to(self.examples_dir)
            content = file.read_text(encoding="utf-8")
            result.append({
                "path": str(rel),
                "size": len(content),
            })
        return result
    
    def get_registry_info(self) -> list[dict]:
        """获取参考案例注册表信息（用于调试）"""
        return [
            {
                "id": ref["id"],
                "file": ref["file"],
                "tech": ref["tech"],
                "subjects": ref["subjects"],
                "branches": ref["branches"],
                "description": ref["description"],
                "keywords_count": len(ref["keywords"])
            }
            for ref in self.REFERENCE_REGISTRY
        ]


example_manager = ExampleManager()
