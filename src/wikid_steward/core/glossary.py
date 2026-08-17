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
    aliases: list[str]
    slug: str = ""
    description: str = ""


class GlossaryExtractor:
    """LLM (gemma4:latest / OpenAI 互換 API) を利用して

    ドキュメントから重要用語・概念を抽出するモジュール。
    """

    def __init__(self, llm_client: OpenAICompatibleLLMClient | None = None):
        self.llm_client = llm_client or OpenAICompatibleLLMClient()

    def extract_terms(
        self, text: str, max_chars: int | None = None
    ) -> list[GlossaryTerm]:
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

        input_text = text[:max_chars] if (max_chars and max_chars > 0) else text
        user_prompt = f"以下の本文から専門用語を抽出してください:\n\n{input_text}"

        try:
            raw_response = self.llm_client.generate_chat_completion(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
            )

            # JSON 部分のパース (マークダウンコードブロック、配列の探索、オブジェクトの救出)
            json_str = raw_response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            # 配列 [...] または オブジェクト {...} の探索
            match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", json_str)
            if match:
                json_str = match.group(0)

            items = []
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    items = parsed
                elif isinstance(parsed, dict):
                    # {"terms": [...]} または単一の {"canonical_title": ...}
                    if "terms" in parsed and isinstance(parsed["terms"], list):
                        items = parsed["terms"]
                    elif "concepts" in parsed and isinstance(parsed["concepts"], list):
                        items = parsed["concepts"]
                    elif "canonical_title" in parsed:
                        items = [parsed]
            except Exception:
                # 行単位の簡易フォールバック
                pass

            terms = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get("canonical_title", "").strip()
                if not title or len(title) <= 2:
                    continue

                slug = generate_slug(title)
                aliases = item.get("aliases", [title])
                if isinstance(aliases, str):
                    aliases = [aliases]
                desc = item.get("description", "")

                terms.append(
                    GlossaryTerm(
                        canonical_title=title,
                        slug=slug,
                        aliases=aliases,
                        description=desc,
                    )
                )

            if terms:
                return terms

        except Exception as e:
            logger.warning(f"Glossary extraction warning: {e}")

        # フェイルセーフ: LLM応答が空または失敗した場合のルールベース主要用語救出
        fallback_terms = []
        # 大見出しやタイトルの単語から主要専門用語を探索
        heading_matches = re.findall(r"^#+\s+(.+)$", text, flags=re.MULTILINE)
        for h in heading_matches[:3]:
            h_clean = h.strip("#").strip()
            if len(h_clean) > 3 and not h_clean.startswith("概要") and not h_clean.startswith("目次"):
                slug = generate_slug(h_clean)
                fallback_terms.append(
                    GlossaryTerm(
                        canonical_title=h_clean,
                        slug=slug,
                        aliases=[h_clean],
                        description=f"Auto-extracted key concept from heading: {h_clean}",
                    )
                )

        # 固有名詞・頭字語のパターンマッチ (例: LoRA, RAG, BERT, GPT 等)
        acronyms = set(re.findall(r"\b[A-Z][A-Za-z0-9-]{2,15}\b", text[:3000]))
        stop_words = {"The", "This", "That", "With", "From", "Using", "Paper", "Model", "Method", "Figure", "Table"}
        for acr in sorted(acronyms - stop_words):
            if len(fallback_terms) >= 5:
                break
            slug = generate_slug(acr)
            if not any(t.slug == slug for t in fallback_terms):
                fallback_terms.append(
                    GlossaryTerm(
                        canonical_title=acr,
                        slug=slug,
                        aliases=[acr],
                        description=f"Auto-extracted domain concept: {acr}",
                    )
                )

        return fallback_terms

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
