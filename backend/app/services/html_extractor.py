"""从AI输出中提取纯HTML代码"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HTMLExtractor:
    """从AI的流式输出中提取HTML代码块"""

    # CDN资源默认值（用于修复或注入）
    DEFAULT_CDNS = {
        "tailwind": "https://cdn.tailwindcss.com/3.4.17",
        "fontawesome_css": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css",
        "threejs": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
        "mathjax": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
    }

    def extract_html(self, raw_text: str) -> str:
        """从AI输出中提取HTML代码

        支持以下格式:
        1. ```html ... ``` 代码块
        2. 直接以 <!DOCTYPE html> 或 <html 开头的内容
        3. 从混合内容中提取HTML部分
        """
        if not raw_text:
            logger.warning("[HTMLExtractor] 输入为空")
            return ""

        logger.info(f"[HTMLExtractor] 开始提取HTML | 输入长度={len(raw_text)}")

        # 尝试从代码块中提取
        pattern = r'```html\s*\n?(.*?)```'
        matches = re.findall(pattern, raw_text, re.DOTALL)
        if matches:
            # 取最长的匹配（通常是完整的HTML）
            html = max(matches, key=len).strip()
            logger.info(f"[HTMLExtractor] 从 ```html``` 代码块中提取 | 匹配模式=代码块 | 提取长度={len(html)}")
            return self._post_process(html)

        # 尝试直接匹配完整HTML文档
        pattern2 = r'(<!DOCTYPE html>.*?</html>)'
        matches2 = re.findall(pattern2, raw_text, re.DOTALL | re.IGNORECASE)
        if matches2:
            html = max(matches2, key=len).strip()
            logger.info(f"[HTMLExtractor] 从 DOCTYPE 匹配中提取 | 匹配模式=DOCTYPE | 提取长度={len(html)}")
            return self._post_process(html)

        # 尝试匹配 <html>...</html>（没有DOCTYPE的情况）
        pattern3 = r'(<html.*?>.*?</html>)'
        matches3 = re.findall(pattern3, raw_text, re.DOTALL | re.IGNORECASE)
        if matches3:
            html = max(matches3, key=len).strip()
            logger.info(f"[HTMLExtractor] 从 <html> 标签匹配中提取 | 匹配模式=html标签 | 提取长度={len(html)}")
            return self._post_process(html)

        # 如果没有找到完整HTML，尝试更宽松的匹配
        if '<html' in raw_text.lower():
            start = raw_text.lower().find('<html')
            # 从 <html 开始到最后一个 </html>
            end = raw_text.lower().rfind('</html>')
            if end > start:
                html = raw_text[start:end + 7].strip()
                logger.info(f"[HTMLExtractor] 从宽松匹配中提取 | 匹配模式=宽松 | 提取长度={len(html)}")
                return self._post_process(html)

        # 最后返回原始文本（可能AI直接输出了HTML而没有代码块标记）
        if raw_text.strip().startswith('<!DOCTYPE') or raw_text.strip().startswith('<html'):
            logger.info(f"[HTMLExtractor] 输入已是HTML，直接返回 | 匹配模式=直接 | 长度={len(raw_text.strip())}")
            return self._post_process(raw_text.strip())

        logger.warning(f"[HTMLExtractor] 未能提取到HTML代码块，返回原始文本 | 输入长度={len(raw_text)}")
        return raw_text.strip()

    def _post_process(self, html: str) -> str:
        """HTML后处理：确保基本结构完整"""
        # 移除可能的前导/后缀空白
        html = html.strip()

        # 确保有DOCTYPE
        if not html.lower().startswith('<!doctype'):
            html = '<!DOCTYPE html>\n' + html

        # 确保有charset meta
        if 'charset' not in html.lower() and '<head>' in html.lower():
            html = html.replace('<head>', '<head>\n    <meta charset="UTF-8">', 1)

        # 确保有viewport meta（响应式）
        if 'viewport' not in html.lower() and '<head>' in html.lower():
            viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            # 尝试在charset之后插入
            if '<meta charset' in html.lower():
                # 找到charset meta的结束位置
                match = re.search(r'<meta\s+charset[^>]*>', html, re.IGNORECASE)
                if match:
                    insert_pos = match.end()
                    html = html[:insert_pos] + '\n    ' + viewport_meta + html[insert_pos:]
            else:
                html = html.replace('<head>', '<head>\n    ' + viewport_meta, 1)

        return html

    def build_streaming_html(self, chunks: list[str]) -> str:
        """将流式接收的文本块合并并提取HTML"""
        full_text = "".join(chunks)
        return self.extract_html(full_text)

    def validate_html(self, html: str) -> dict:
        """验证HTML的基本完整性

        Returns:
            {
                "valid": True/False,
                "has_doctype": True/False,
                "has_html_tag": True/False,
                "has_head": True/False,
                "has_body": True/False,
                "has_tailwind": True/False,
                "has_fontawesome": True/False,
                "char_count": int,
                "issues": ["缺少..."]
            }
        """
        html_lower = html.lower()
        issues = []

        has_doctype = '<!doctype html>' in html_lower
        has_html_tag = '<html' in html_lower and '</html>' in html_lower
        has_head = '<head>' in html_lower and '</head>' in html_lower
        has_body = '<body' in html_lower and '</body>' in html_lower
        has_tailwind = 'tailwindcss' in html_lower or 'tailwind' in html_lower
        has_fontawesome = 'font-awesome' in html_lower or 'fontawesome' in html_lower

        if not has_doctype:
            issues.append("缺少 DOCTYPE 声明")
        if not has_html_tag:
            issues.append("缺少完整的 <html> 标签")
        if not has_head:
            issues.append("缺少 <head> 部分")
        if not has_body:
            issues.append("缺少 <body> 部分")
        if not has_tailwind:
            issues.append("未检测到 Tailwind CSS")
        if not has_fontawesome:
            issues.append("未检测到 Font Awesome")

        return {
            "valid": has_html_tag and has_head and has_body,
            "has_doctype": has_doctype,
            "has_html_tag": has_html_tag,
            "has_head": has_head,
            "has_body": has_body,
            "has_tailwind": has_tailwind,
            "has_fontawesome": has_fontawesome,
            "char_count": len(html),
            "issues": issues
        }


# 全局单例
html_extractor = HTMLExtractor()
