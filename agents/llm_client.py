"""OpenRouter LLM client."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .config import ModelConfig


@dataclass
class LLMResponse:
    """Response from LLM API."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenRouterClient:
    """Client for OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str | None = None, timeout: float = 120.0):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var "
                "or pass api_key parameter."
            )
        self.timeout = timeout

    def chat(
        self,
        model: ModelConfig,
        messages: list[dict[str, str]],
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            model: Model configuration
            messages: List of message dicts with 'role' and 'content'

        Returns:
            LLMResponse with generated content and token usage
        """
        payload = {
            "model": model.id,
            "messages": messages,
            "max_tokens": model.max_tokens,
            "temperature": model.temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/saotri-bench",
            "X-Title": "Saotri Bench Agent",
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.BASE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Parse response
        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", model.id),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

    def generate_code(
        self,
        model: ModelConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate code from a prompt, extracting Python code from response.

        Args:
            model: Model configuration
            system_prompt: System message
            user_prompt: User message with task details

        Returns:
            Extracted Python code string
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.chat(model, messages)
        return self._extract_code(response.content)

    @staticmethod
    def _extract_code(text: str) -> str:
        """Extract Python code from LLM response.

        Handles:
        - ```python ... ``` / ```py ... ``` / ```Python ... ``` blocks
        - ``` ... ``` blocks (generic)
        - Raw code with function definitions
        - Tolerates missing newline after language tag (common with Gemini)
        """
        # Try ```python or ```py blocks (case-insensitive, flexible whitespace)
        pattern = r"```(?:python|py)\s*(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            code = max(matches, key=len).strip()
            if code:
                return code

        # Try generic code blocks
        pattern = r"```\s*(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # Filter out blocks that look like language-only tags (e.g. "json\n{...}")
            python_matches = [
                m.strip() for m in matches
                if "def " in m and m.strip()
            ]
            if python_matches:
                return max(python_matches, key=len)
            # Fallback to longest non-empty block
            non_empty = [m.strip() for m in matches if m.strip()]
            if non_empty:
                return max(non_empty, key=len)

        # If no code blocks, try to find function definition in raw text
        lines = text.split("\n")
        code_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith("def "):
                in_code = True
            if in_code:
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines).strip()

        # Last resort: return the whole thing (let evaluator report syntax error
        # rather than "empty solution" which wastes an attempt with no feedback)
        return text.strip()
