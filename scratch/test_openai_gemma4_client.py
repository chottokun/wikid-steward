from wikid_steward.core.llm_client import LLMConfig, OpenAICompatibleLLMClient

def test_gemma4_openai_compatibility():
    print("=== Testing OpenAI-Compatible Client with Ollama gemma4:latest ===")
    config = LLMConfig(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="gemma4:latest",
    )

    client = OpenAICompatibleLLMClient(config=config)
    print(f"Connecting to {config.base_url} with model {config.model}...")

    prompt = "次の文章から、主要な専門用語をJSON形式のリスト（['用語1', '用語2']）で返してください:\n\n'LLM-as-a-judge is an evaluation paradigm using Large Language Models to score AI outputs.'"
    
    try:
        response = client.generate_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="あなたはJSONのみを出力する優秀なテキスト解析AIです。"
        )

        print("\n✅ Response Received from gemma4:latest:")
        print(response)

    except Exception as e:
        print(f"\n⚠️ Error connecting to gemma4:latest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemma4_openai_compatibility()
