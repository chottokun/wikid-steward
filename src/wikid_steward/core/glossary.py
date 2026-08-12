import json
import re
from dataclasses import dataclass
from pathlib import Path
from wikid_steward.core.llm_client import LLMConfig, OpenAICompatibleLLMClient
from wikid_steward.core.okf_converter import generate_okf_frontmatter
from wikid_steward.core.slug import generate_slug


@dataclass
class GlossaryTerm:
    canonical_title: str
    slug: str
    aliases: list[str]
    description: str


class GlossaryExtractor:
    """LLM (gemma4:latest / OpenAI 互換 API) を利用して

    ドキュメントから重要用語・概念を抽出するモジュール。
    """

    def __init__(self, llm_client: OpenAICompatibleLLMClient | None = None):
        self.llm_client = llm_client or OpenAICompatibleLLMClient()

    def extract_terms(self, text: str) -> list[GlossaryTerm]:
        """テキストから主要な専門用語リストを抽出する"""
        system_prompt = (
            "あなたは高度な技術文書・論文の用語解析AIです。"
            "テキストから重要で専門性の高い概念・用語（Key Terms / Concepts）を抽出し、"
            "必ず以下のJSON配列形式のみで出力してください。"
            "一般名詞（data, file, output, AI, NLP など）や単なる一般的な単語は除外してください。\n\n"
            "JSON出力形式:\n"
            "[\n"
            "  {\n"
            '    "canonical_title": "LLM-as-a-judge",\n'
            '    "aliases": ["LLM as a judge", "LLM-as-a-Judge"],\n'
            '    "description": "大規模言語モデルを評価者として用いる評価手法。"\n'
            "  }\n"
            "]"
        )

        user_prompt = f"以下の本文から専門用語を抽出してください:\n\n{text[:3000]}"

        try:
            raw_response = self.llm_client.generate_chat_completion(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
            )

            # JSON 部分のパース
            json_str = raw_response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            json_str = json_str.strip()
            items = json.loads(json_str)

            terms = []
            for item in items:
                title = item.get("canonical_title", "").strip()
                if not title or len(title) <= 2:
                    continue

                slug = generate_slug(title)
                aliases = item.get("aliases", [title])
                desc = item.get("description", "")

                terms.append(
                    GlossaryTerm(
                        canonical_title=title,
                        slug=slug,
                        aliases=aliases,
                        description=desc,
                    )
                )

            return terms

        except Exception as e:
            print(f"Glossary extraction warning: {e}")
            return []

    def create_glossary_note(
        self, term: GlossaryTerm, output_dir: Path
    ) -> Path:
        """用語説明ノート (wiki/glossary/{slug}.md) を保存する"""
        output_dir.mkdir(parents=True, exist_ok=True)
        note_path = output_dir / f"{term.slug}.md"

        custom_meta = {"aliases": term.aliases, "doc_type": "Glossary Term"}

        frontmatter = generate_okf_frontmatter(
            doc_id=f"glossary_{term.slug}",
            title=term.canonical_title,
            doc_type="Glossary Term",
            source_path="",
            custom_metadata=custom_meta,
        )

        body = (
            f"# {term.canonical_title}\n\n"
            f"## 概要\n{term.description}\n\n"
            f"## 別名・表記揺れ\n"
            + "\n".join([f"- {alias}" for alias in term.aliases])
        )

        note_content = f"{frontmatter}\n{body}\n"
        note_path.write_text(note_content, encoding="utf-8")
        return note_path
