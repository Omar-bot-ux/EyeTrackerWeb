"""
SuggestionGenerator: Provides intelligent word (fill-mask) and phrase (text-generation)
suggestions using Hugging Face transformers, with caching, graceful fallbacks,
and support for patient response mapping.

Requirements:
- transformers
- torch (or accelerate-supported backend)

This class loads pipelines lazily to keep startup fast. If models cannot be
loaded (e.g., no internet or missing weights), it gracefully falls back to a
common-words list for word suggestions and simple template-based phrase
suggestions.
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from transformers import pipeline
    _TRANSFORMERS_AVAILABLE = True
except Exception:  # pragma: no cover - environment may lack transformers
    pipeline = None  # type: ignore
    _TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SuggestionConfig:
    """Configuration controlling models and behavior."""
    # Model ids can be customized if you mirror models locally
    fill_mask_model: str = "bert-base-uncased"  # supports fill-mask via pipeline(task="fill-mask")
    text_gen_model: str = "gpt2"  # small model for short generations

    # Limits and thresholds
    max_word_suggestions: int = 5
    max_phrase_suggestions: int = 3
    max_gen_tokens: int = 24  # short phrases

    # Caching
    enable_cache: bool = True

    # Fallback words used when model is not available or input too short
    fallback_common_words: Tuple[str, ...] = (
        "yes", "no", "okay", "thanks", "please", "help", "more", "stop",
        "pain", "water", "tired", "hungry", "bathroom", "doctor",
    )

    # Mapping from short patient responses to canonical intents or richer phrasing
    patient_response_map: Dict[str, str] = field(
        default_factory=lambda: {
            "yes": "affirmative",
            "no": "negative",
            "help": "request_help",
            "water": "request_water",
            "bathroom": "request_bathroom",
            "pain": "report_pain",
            "tired": "report_fatigue",
            "hungry": "request_food",
            "stop": "request_stop",
        }
    )


class SuggestionGenerator:
    """Generates word and phrase suggestions.

    Key features:
    - Word suggestions via masked language modeling (fill-mask) when context
      contains a [MASK] token, else falls back to common words.
    - Phrase suggestions via a small text-generation model.
    - Caching for repeat queries to reduce latency and API/model calls.
    - Fallback behavior when transformers/models are unavailable.
    - Patient response mapping to help downstream systems interpret user intent.
    """

    MASK_TOKEN = "[MASK]"

    def __init__(self, config: Optional[SuggestionConfig] = None):
        self.config = config or SuggestionConfig()
        self._fill_mask_pipe = None
        self._text_gen_pipe = None

        # Internal caches
        self._cache_word: Dict[Tuple[str, int], List[str]] = {}
        self._cache_phrase: Dict[Tuple[str, int, int], List[str]] = {}

    # ---------- Lazy loader helpers ----------
    def _get_fill_mask_pipe(self):
        if not _TRANSFORMERS_AVAILABLE:
            return None
        if self._fill_mask_pipe is None:
            try:
                self._fill_mask_pipe = pipeline(
                    task="fill-mask",
                    model=self.config.fill_mask_model,
                )
            except Exception as e:  # pragma: no cover
                logger.warning("Fill-mask pipeline unavailable: %s", e)
                self._fill_mask_pipe = None
        return self._fill_mask_pipe

    def _get_text_gen_pipe(self):
        if not _TRANSFORMERS_AVAILABLE:
            return None
        if self._text_gen_pipe is None:
            try:
                self._text_gen_pipe = pipeline(
                    task="text-generation",
                    model=self.config.text_gen_model,
                )
            except Exception as e:  # pragma: no cover
                logger.warning("Text-generation pipeline unavailable: %s", e)
                self._text_gen_pipe = None
        return self._text_gen_pipe

    # ---------- Public API ----------
    def suggest_words(self, context: str, limit: Optional[int] = None) -> List[str]:
        """Suggest likely words for a masked context.

        Usage:
            - Provide a sentence containing the token "[MASK]" to get model-based
              completions for that position.
            - If no mask present or model unavailable, returns common fallback words.

        Args:
            context: A string that may include a [MASK] token.
            limit: Optional cap on number of suggestions.

        Returns:
            A list of suggested words (strings), unique and ordered by model score
            when applicable.
        """
        if not context:
            return list(self.config.fallback_common_words)[: limit or self.config.max_word_suggestions]

        limit = limit or self.config.max_word_suggestions
        cache_key = (context, limit)
        if self.config.enable_cache and cache_key in self._cache_word:
            return self._cache_word[cache_key]

        suggestions: List[str] = []

        if self.MASK_TOKEN in context:
            fill_mask = self._get_fill_mask_pipe()
            if fill_mask is not None:
                try:
                    results = fill_mask(context)
                    # transformers returns a dict or list depending on model; normalize to list
                    if isinstance(results, dict):
                        results = [results]
                    for item in results[:limit * 2]:  # fetch extra to deduplicate later
                        token_str = item.get("token_str") or item.get("sequence") or ""
                        token_str = token_str.strip()
                        if token_str:
                            suggestions.append(token_str)
                except Exception as e:  # pragma: no cover
                    logger.warning("fill-mask suggestion failed: %s", e)

        if not suggestions:
            # Fallback when no mask or pipeline unavailable
            suggestions = list(self.config.fallback_common_words)

        # Deduplicate while preserving order, then truncate
        seen = set()
        unique: List[str] = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
            if len(unique) >= limit:
                break

        if self.config.enable_cache:
            self._cache_word[cache_key] = unique
        return unique

    def suggest_phrases(self, prompt: str, limit: Optional[int] = None, max_new_tokens: Optional[int] = None) -> List[str]:
        """Suggest short phrases that continue a prompt.

        Args:
            prompt: The initial text to continue.
            limit: Number of suggestions to return.
            max_new_tokens: How many new tokens to generate per suggestion.
        """
        limit = limit or self.config.max_phrase_suggestions
        max_new_tokens = max_new_tokens or self.config.max_gen_tokens

        cache_key = (hash(prompt), limit, max_new_tokens)
        if self.config.enable_cache and cache_key in self._cache_phrase:
            return self._cache_phrase[cache_key]

        suggestions: List[str] = []

        gen = self._get_text_gen_pipe()
        if gen is not None and prompt:
            try:
                outputs = gen(
                    prompt,
                    num_return_sequences=limit,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    top_p=0.92,
                    top_k=50,
                    temperature=0.8,
                    pad_token_id=50256 if "gpt2" in self.config.text_gen_model else None,
                )
                for out in outputs:
                    text = out.get("generated_text", "").strip()
                    if text:
                        # Keep only the continuation after the prompt when possible
                        if text.startswith(prompt):
                            cont = text[len(prompt):].strip()
                            suggestions.append(cont if cont else text)
                        else:
                            suggestions.append(text)
            except Exception as e:  # pragma: no cover
                logger.warning("text-generation failed: %s", e)

        if not suggestions:
            # Simple template fallback suggestions
            base = prompt.strip() if prompt else ""
            templates = [
                f"{base} yes.",
                f"{base} no.",
                f"{base} please.",
                f"{base} I need help.",
                f"{base} thank you.",
            ]
            suggestions = [s.strip() for s in templates][:limit]

        # Deduplicate preserve order
        seen = set()
        unique: List[str] = []
        for s in suggestions:
            if s and s not in seen:
                seen.add(s)
                unique.append(s)
            if len(unique) >= limit:
                break

        if self.config.enable_cache:
            self._cache_phrase[cache_key] = unique
        return unique

    def map_patient_response(self, text: str) -> Optional[str]:
        """Map a short patient response to a canonical intent string.

        Returns a value like "request_help" or "report_pain" when a mapping is
        found; otherwise returns None.
        """
        if not text:
            return None
        key = text.strip().lower()
        return self.config.patient_response_map.get(key)


__all__ = [
    "SuggestionConfig",
    "SuggestionGenerator",
]
