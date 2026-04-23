"""多级目录提示词管理器 - 从文件系统加载并组装提示词"""
import logging
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class PromptManager:
    """提示词管理器
    
    提示词层级:
    L1: system/         - 系统角色设定
    L2: subjects/       - 学科专项提示词
    L3: scenes/         - 场景类型提示词
    L4: quality/        - 质量约束提示词
    
    最终Prompt = L1 + L2 + L3 + L4 + 用户输入
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or settings.PROMPTS_DIR
    
    def _read_file(self, relative_path: str) -> str:
        """读取提示词文件内容，支持热更新（每次请求重新读取）"""
        file_path = self.prompts_dir / relative_path
        try:
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8").strip()
                # 忽略纯注释占位文件（只有一行且以#开头但不是##标题）
                # Markdown标题 ## 开头的是有效内容
                if content:
                    first_line = content.split('\n')[0].strip()
                    # 如果第一行是 "# 待后续..." 这种占位注释，忽略
                    if first_line.startswith('#') and not first_line.startswith('##') and '待' in first_line:
                        return ""
                    return content
        except Exception as e:
            logger.warning(f"读取提示词文件失败 {relative_path}: {e}")
        return ""
    
    def get_system_prompt(self) -> str:
        """获取L1系统角色提示词"""
        return self._read_file("system/base_role.txt")
    
    def get_subject_prompt(self, subject: str, branch: Optional[str] = None) -> str:
        """获取L2学科提示词
        
        Args:
            subject: 学科，如 "math", "physics", "chemistry"
            branch: 分支，如 "geometry", "optics"
        """
        parts = []
        # 先读学科总纲
        index_prompt = self._read_file(f"subjects/{subject}/_index.txt")
        if index_prompt:
            parts.append(index_prompt)
        # 再读具体分支
        if branch:
            branch_prompt = self._read_file(f"subjects/{subject}/{branch}.txt")
            if branch_prompt:
                parts.append(branch_prompt)
        return "\n\n".join(parts)
    
    def get_scene_prompt(self, scene_type: str) -> str:
        """获取L3场景类型提示词"""
        return self._read_file(f"scenes/{scene_type}.txt")
    
    def get_quality_prompts(self, include_rules: bool = False) -> str:
        """获取L4质量约束提示词
        
        Args:
            include_rules: 是否包含详细规则文件（interaction_rules等）。
                           默认False，因为完整参考案例已示范所有规则。
        """
        if not include_rules:
            # 精简模式：不加载详细规则，完整参考案例已包含所有规范
            return ""
        
        quality_dir = self.prompts_dir / "quality"
        parts = []
        if quality_dir.exists():
            for txt_file in sorted(quality_dir.glob("*.txt")):
                content = txt_file.read_text(encoding="utf-8").strip()
                if content:
                    first_line = content.split('\n')[0].strip()
                    # 跳过占位文件
                    if first_line.startswith('#') and not first_line.startswith('##') and '待' in first_line:
                        continue
                    parts.append(content)
        return "\n\n".join(parts)
    
    def assemble_prompt(
        self,
        subject: str,
        branch: Optional[str] = None,
        scene_type: Optional[str] = None,
        user_input: str = "",
    ) -> list[dict]:
        """组装完整的消息列表
        
        Returns:
            OpenAI格式消息列表 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        logger.info(f"[PromptManager] 开始组装提示词 | subject={subject} | branch={branch} | scene_type={scene_type}")
        
        # 组装系统提示词
        system_parts = []
        
        # L1: 系统角色
        l1 = self.get_system_prompt()
        if l1:
            system_parts.append(l1)
            logger.info(f"[PromptManager] L1-系统角色加载成功 | 长度={len(l1)}")
        else:
            logger.warning("[PromptManager] L1-系统角色未找到")
        
        # L2: 学科专项
        l2 = self.get_subject_prompt(subject, branch)
        if l2:
            system_parts.append(l2)
            logger.info(f"[PromptManager] L2-学科专项加载成功 | subject={subject} | branch={branch} | 长度={len(l2)}")
        else:
            logger.info(f"[PromptManager] L2-学科专项未找到 | subject={subject} | branch={branch}")
        
        # L3: 场景类型
        if scene_type:
            l3 = self.get_scene_prompt(scene_type)
            if l3:
                system_parts.append(l3)
                logger.info(f"[PromptManager] L3-场景类型加载成功 | scene_type={scene_type} | 长度={len(l3)}")
            else:
                logger.info(f"[PromptManager] L3-场景类型未找到 | scene_type={scene_type}")
        
        # L4: 质量约束（默认不加载详细规则，完整参考案例已示范）
        # 如需启用详细规则，传入 include_quality_rules=True
        # l4 = self.get_quality_prompts(include_rules=True)
        # if l4:
        #     system_parts.append(l4)
        
        system_content = "\n\n---\n\n".join(system_parts)
        
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": user_input})
        
        total_system_len = len(system_content)
        logger.info(f"[PromptManager] 提示词组装完成 | 系统提示词总长度={total_system_len}")
        logger.debug(f"[PromptManager] 系统提示词预览（前500字符）:\n{system_content[:500]}...")
        
        return messages
    
    def list_available_prompts(self) -> dict:
        """列出所有可用的提示词文件（用于调试）"""
        result = {"system": [], "subjects": {}, "scenes": [], "quality": []}
        
        # System
        system_dir = self.prompts_dir / "system"
        if system_dir.exists():
            result["system"] = [f.name for f in system_dir.glob("*.txt")]
        
        # Subjects
        subjects_dir = self.prompts_dir / "subjects"
        if subjects_dir.exists():
            for subject_dir in subjects_dir.iterdir():
                if subject_dir.is_dir():
                    result["subjects"][subject_dir.name] = [f.name for f in subject_dir.glob("*.txt")]
        
        # Scenes
        scenes_dir = self.prompts_dir / "scenes"
        if scenes_dir.exists():
            result["scenes"] = [f.name for f in scenes_dir.glob("*.txt")]
        
        # Quality
        quality_dir = self.prompts_dir / "quality"
        if quality_dir.exists():
            result["quality"] = [f.name for f in quality_dir.glob("*.txt")]
        
        return result


# 全局单例
prompt_manager = PromptManager()
