"""HTML后处理器 - 清理和修复AI生成的HTML"""
import re
import logging

logger = logging.getLogger(__name__)


class PostProcessor:
    """对AI生成的HTML进行后处理"""
    
    # 推荐的CDN地址
    RECOMMENDED_CDNS = {
        "tailwind": "https://cdn.tailwindcss.com/3.4.17",
        "fontawesome": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css",
        "threejs": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
        "orbit_controls": "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js",
        "mathjax": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
    }
    
    def process(self, html: str) -> str:
        """完整后处理流程"""
        original_len = len(html)
        logger.info(f"[PostProcessor] 开始后处理 | 输入长度={original_len}")
        
        fixes_applied = []
        
        html = self._ensure_doctype(html)
        if not html.strip().lower().startswith('<!doctype'):
            fixes_applied.append("添加DOCTYPE")
        
        if 'charset' not in html.lower():
            html = self._ensure_charset(html)
            fixes_applied.append("添加charset")
        else:
            html = self._ensure_charset(html)
        
        if 'viewport' not in html.lower():
            html = self._ensure_viewport(html)
            fixes_applied.append("添加viewport")
        else:
            html = self._ensure_viewport(html)
        
        html = self._fix_cdn_links(html)
        
        final_len = len(html)
        logger.info(f"[PostProcessor] 后处理完成 | 输入长度={original_len} | 输出长度={final_len} | 修复操作={fixes_applied if fixes_applied else '无'}")
        
        return html
    
    def _ensure_doctype(self, html: str) -> str:
        if not html.strip().lower().startswith('<!doctype'):
            html = '<!DOCTYPE html>\n' + html
        return html
    
    def _ensure_charset(self, html: str) -> str:
        if 'charset' not in html.lower() and '<head>' in html.lower():
            html = html.replace('<head>', '<head>\n    <meta charset="UTF-8">', 1)
        return html
    
    def _ensure_viewport(self, html: str) -> str:
        if 'viewport' not in html.lower() and '<head>' in html.lower():
            html = html.replace(
                '<meta charset="UTF-8">',
                '<meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
                1
            )
        return html
    
    def _fix_cdn_links(self, html: str) -> str:
        """修复可能失效的CDN链接"""
        # 替换已知的失效CDN模式
        replacements = {
            # Tailwind旧链接 → 新链接
            'cdn.tailwindcss.com"': 'cdn.tailwindcss.com/3.4.17"',
        }
        for old, new in replacements.items():
            if old in html and new not in html:
                html = html.replace(old, new)
        return html


post_processor = PostProcessor()
