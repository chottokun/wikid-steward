from dataclasses import dataclass

from openai import OpenAI

from wikid_steward.core.config import get_config


@dataclass
class LLMConfig:
    """OpenAI 互換 API 接続設定データクラス"""

    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout: float = 5.0

    def __post_init__(self):
        global_cfg = get_config()
        if not self.base_url:
            self.base_url = global_cfg.llm.base_url
        if not self.api_key:
            self.api_key = global_cfg.llm.api_key
        if not self.model:
            self.model = global_cfg.llm.model


class OpenAICompatibleLLMClient:
    """OpenAI 互換 API (Ollama, OpenAI, Custom LLM) を一元的に呼び出すクライアント"""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key or "ollama",
            timeout=self.config.timeout,
        )

    def generate_chat_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        model_override: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """OpenAI 互換 chat/completions API を実行しテキストを返却する。"""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        model = model_override or self.config.model
        temp = temperature if temperature is not None else self.config.temperature

        response = self.client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=temp,
            max_tokens=self.config.max_tokens,
        )

        content = response.choices[0].message.content
        return content.strip() if content else ""

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model_override: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """単一プロンプトからテキストを生成する簡易インターフェース"""
        messages = [{"role": "user", "content": prompt}]
        return self.generate_chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            model_override=model_override,
            temperature=temperature,
        )
