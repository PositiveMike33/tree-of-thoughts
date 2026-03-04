"""
OpenRouter Configuration and LLM Client Management

Handles configuration loading from environment variables and
provides a factory function for creating OpenRouter LLM clients.
"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM provider and model settings."""
    provider: str  # "openrouter"
    api_key: str  # API key from environment
    model: str = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
    api_base: Optional[str] = None
    max_tokens: int = 5000
    temperature: float = 0.7
    timeout: int = 60

    @staticmethod
    def from_env() -> Optional['LLMConfig']:
        """Load configuration from .env file.

        Returns:
            LLMConfig: Configuration with validated credentials

        Raises:
            ValueError: If required API key is missing
        """
        # Load from .env if it exists
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment. "
                "Please set it in .env file or environment variables."
            )

        model = os.getenv(
            "OPENROUTER_MODEL",
            "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
        )

        return LLMConfig(
            provider="openrouter",
            model=model,
            api_key=api_key,
            api_base=os.getenv("OPENROUTER_API_BASE"),
            max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "5000")),
            temperature=float(os.getenv("OPENROUTER_TEMPERATURE", "0.7")),
            timeout=int(os.getenv("OPENROUTER_TIMEOUT", "60"))
        )


class OpenRouterClient:
    """HTTP Client for OpenRouter API interactions."""

    def __init__(self, config: LLMConfig):
        """Initialize OpenRouter client with configuration.

        Args:
            config: LLMConfig instance with API credentials
        """
        self.config = config
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "HTTP-Referer": "https://github.com/kyegomez/tree-of-thoughts",
            "X-Title": "Tree of Thoughts - Vault Integration"
        })

    def call(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate response from OpenRouter API.

        Args:
            prompt: User prompt/question
            system_prompt: System instructions
            temperature: Response creativity (0-2)
            max_tokens: Maximum tokens in response

        Returns:
            Generated response text

        Raises:
            requests.RequestException: If API call fails
        """
        if temperature is None:
            temperature = self.config.temperature
        if max_tokens is None:
            max_tokens = self.config.max_tokens

        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 1.0,
            "repetition_penalty": 1.0,
        }

        try:
            logger.info(f"Calling OpenRouter with model: {self.config.model}")
            response = self.session.post(
                url,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            data = response.json()

            # Extract content from response
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                tokens_used = usage.get("completion_tokens", 0)

                logger.info(f"OpenRouter response received ({tokens_used} tokens)")
                return content
            else:
                raise ValueError("Unexpected response format from OpenRouter")

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing OpenRouter response: {e}")
            raise


class OpenRouterConfigManager:
    """Manager for OpenRouter configuration and client creation."""

    @staticmethod
    def load_from_env() -> LLMConfig:
        """Load configuration from environment.

        Returns:
            LLMConfig instance

        Raises:
            ValueError: If required configuration is missing
        """
        return LLMConfig.from_env()

    @staticmethod
    def create_llm_client(config: Optional[LLMConfig] = None) -> OpenRouterClient:
        """Factory function to create OpenRouter LLM client.

        Args:
            config: LLMConfig instance. If None, loads from environment.

        Returns:
            OpenRouterClient configured for API calls

        Raises:
            ValueError: If configuration cannot be loaded
        """
        if config is None:
            config = OpenRouterConfigManager.load_from_env()

        return OpenRouterClient(config)
