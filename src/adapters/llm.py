"""Modular LLM adapter interface supporting Google Gemini by default."""

import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class BaseLLMAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generates text from the given prompt and system instruction."""
        pass


class GeminiAdapter(BaseLLMAdapter):
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self._client = None

        if not self.api_key:
            print("[Warning] GEMINI_API_KEY is not set in environment or .env. LLM calls will fail until set.")

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided to perform LLM calls.")

        client = self._get_client()
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.1,
            }
        )
        return response.text or ""


class MockLLMAdapter(BaseLLMAdapter):
    """Deterministic mock adapter for testing without API keys."""
    def __init__(self, default_response: Optional[str] = None):
        self.default_response = default_response or json.dumps({
            "score": 4,
            "skills_overlap": ["Python", "FastAPI"],
            "missing_requirements": ["3+ years production experience"],
            "seniority_fit": "Good fit for intern level",
            "honest_reason": "Strong match on Python/FastAPI backend fundamentals, but lacks large-scale production experience."
        })

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        return self.default_response
