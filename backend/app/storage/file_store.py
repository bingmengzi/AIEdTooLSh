"""本地文件存储 - 保存生成的HTML和元数据"""
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


class FileStore:
    """本地文件存储管理器"""
    
    def __init__(self):
        self.outputs_dir = settings.OUTPUTS_DIR
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
    
    def save_html(self, html_content: str, query: str, dsl: dict = None, provider: str = "") -> str:
        """保存生成的HTML文件和元数据
        
        Args:
            html_content: HTML代码
            query: 用户原始输入
            dsl: Scene DSL数据
            provider: 使用的AI模型
            
        Returns:
            result_id: 唯一标识符
        """
        result_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        logger.info(f"[FileStore] 开始保存 | result_id={result_id} | html_length={len(html_content)}")
        
        # 保存HTML文件
        html_path = self.outputs_dir / f"{result_id}.html"
        html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"[FileStore] HTML已保存 | path={html_path}")
        
        # 保存元数据
        metadata = {
            "id": result_id,
            "query": query,
            "provider": provider,
            "dsl": dsl,
            "created_at": datetime.now().isoformat(),
            "html_file": f"{result_id}.html",
            "html_length": len(html_content),
        }
        meta_path = self.outputs_dir / f"{result_id}.json"
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # 元数据摘要日志
        dsl_topic = dsl.get("topic", "N/A") if dsl else "N/A"
        dsl_scene_type = dsl.get("scene_type", "N/A") if dsl else "N/A"
        logger.info(f"[FileStore] 元数据已保存 | path={meta_path} | query={query[:50]}... | topic={dsl_topic} | scene_type={dsl_scene_type} | provider={provider}")
        
        return result_id
    
    def get_html(self, result_id: str) -> str | None:
        """读取已保存的HTML"""
        html_path = self.outputs_dir / f"{result_id}.html"
        if html_path.exists():
            return html_path.read_text(encoding="utf-8")
        return None
    
    def get_metadata(self, result_id: str) -> dict | None:
        """读取元数据"""
        meta_path = self.outputs_dir / f"{result_id}.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return None
    
    def list_results(self, limit: int = 20) -> list[dict]:
        """列出最近的生成结果"""
        results = []
        for meta_file in sorted(self.outputs_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                results.append({
                    "id": meta.get("id"),
                    "query": meta.get("query"),
                    "created_at": meta.get("created_at"),
                    "provider": meta.get("provider"),
                })
            except Exception:
                continue
        return results


file_store = FileStore()
