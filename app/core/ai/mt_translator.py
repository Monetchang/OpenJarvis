# coding=utf-8
"""
机器翻译器模块（不依赖 LLM）

基于 deep-translator，使用 Google Translate / MyMemory 等免费 API
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .translator import TranslationResult, BatchTranslationResult

MT_BATCH_WORKERS = 8  # 并发翻译线程数

_LANG_MAP = {
    "chinese": "zh-CN",
    "english": "en",
    "japanese": "ja",
    "korean": "ko",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "russian": "ru",
    "portuguese": "pt",
}


def _to_code(name: str) -> str:
    key = (name or "").strip().lower()
    return _LANG_MAP.get(key, "zh-CN" if "chin" in key or "zh" in key else "en")


class MTTranslator:
    """机器翻译器（免费，无需 API Key）"""

    def __init__(self, translation_config: Dict[str, Any]):
        self.enabled = translation_config.get("ENABLED", False)
        self.target_code = _to_code(translation_config.get("LANGUAGE", "Chinese"))

    def translate(self, text: str) -> TranslationResult:
        result = TranslationResult(original_text=text)
        if not self.enabled:
            result.error = "翻译功能未启用"
            return result
        if not text or not text.strip():
            result.translated_text = text
            result.success = True
            return result
        try:
            from deep_translator import GoogleTranslator
            trans = GoogleTranslator(source="auto", target=self.target_code)
            result.translated_text = trans.translate(text)
            result.success = True
        except Exception as e:
            result.error = f"翻译失败: {type(e).__name__}: {str(e)[:80]}"
        return result

    def translate_batch(self, texts: List[str]) -> BatchTranslationResult:
        batch = BatchTranslationResult(total_count=len(texts))
        for text in texts:
            batch.results.append(TranslationResult(original_text=text))
        if not self.enabled:
            for r in batch.results:
                r.error = "翻译功能未启用"
            batch.fail_count = len(texts)
            return batch
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        for i, t in enumerate(texts):
            if not t or not t.strip():
                batch.results[i].translated_text = t
                batch.results[i].success = True
                batch.success_count += 1
        if not non_empty:
            return batch
        try:
            from deep_translator import GoogleTranslator

            def _translate_one(item: tuple) -> tuple:
                idx, text = item
                trans = GoogleTranslator(source="auto", target=self.target_code)
                return (idx, trans.translate(text))

            workers = min(MT_BATCH_WORKERS, len(non_empty))
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(_translate_one, (i, t)): i for i, t in non_empty}
                for future in as_completed(futures):
                    try:
                        idx, translated = future.result()
                        batch.results[idx].translated_text = translated
                        batch.results[idx].success = True
                        batch.success_count += 1
                    except Exception as e:
                        idx = futures[future]
                        batch.results[idx].error = str(e)[:80]
                        batch.fail_count += 1
        except Exception as e:
            err = str(e)[:80]
            for i, _ in non_empty:
                batch.results[i].error = err
            batch.fail_count = len(non_empty)
        return batch
