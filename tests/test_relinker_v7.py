import pytest
from wikid_steward.core.glossary import GlossaryTerm
from wikid_steward.core.relinker import WikiRelinker, convert_wikilinks_to_gfm, convert_gfm_to_wikilinks


def test_relinker_multilingual_and_protected_segments():
    relinker = WikiRelinker()
    terms = [
        GlossaryTerm(canonical_title="システムアーキテクチャ", aliases=["システムアーキテクチャ", "System Architecture"]),
        GlossaryTerm(canonical_title="PID制御", aliases=["PID制御", "PID Control"]),
    ]

    text = """---
type: Concept
title: テスト
---

# システムアーキテクチャ解説

## 概要
ここでは システムアーキテクチャ と PID制御 について解説します。システムアーキテクチャ は重要です。

## コードと数式
```python
# システムアーキテクチャ inside code
x = PID制御()
```
インラインコード `PID制御` や数式 $\\text{PID制御}$ も置換しません。

## HTMLテーブルと手書きメモ
<table border="1">
<tr><td>システムアーキテクチャ</td></tr>
</table>

<!-- HUMAN BEGIN -->
現場メモ: システムアーキテクチャの変更点
<!-- HUMAN END -->

## 第二セクション
新しいセクションでは再度 PID制御 がリンクされますが、2回目 PID制御 はリンクされません。
"""

    relinked, count = relinker.relink_text(text, terms, mode="first_hit_per_section")

    # フロントマター内のタイトルや見出しは保護されているか
    assert "---\ntype: Concept\ntitle: テスト\n---" in relinked
    assert "# システムアーキテクチャ解説" in relinked

    # 概要セクションでは初回のみ置換
    assert "[[システムアーキテクチャ]] と [[PID制御]] について解説します。" in relinked
    assert "について解説します。システムアーキテクチャ は重要です。" in relinked  # 2回目は非置換

    # コードや数式、テーブル、手書きメモ内は保護
    assert "# システムアーキテクチャ inside code" in relinked
    assert "`PID制御`" in relinked
    assert "$\\text{PID制御}$" in relinked
    assert "<tr><td>システムアーキテクチャ</td></tr>" in relinked
    assert "現場メモ: システムアーキテクチャの変更点" in relinked

    # 第二セクションではセクション初回として再度 PID制御 が置換される
    assert "新しいセクションでは再度 [[PID制御]] がリンクされますが、2回目 PID制御 はリンクされません。" in relinked


def test_convert_wikilinks_to_gfm_and_back():
    wiki_map = {
        "システムアーキテクチャ": "concepts/system-architecture.md",
        "PID制御": "concepts/pid-control.md",
    }

    markdown = "詳しくは [[システムアーキテクチャ]] および [[PID制御]] を参照。"
    gfm_text = convert_wikilinks_to_gfm(markdown, wiki_map, base_path="/wiki")

    assert "[システムアーキテクチャ](/wiki/concepts/system-architecture.md)" in gfm_text
    assert "[PID制御](/wiki/concepts/pid-control.md)" in gfm_text

    # 逆変換
    wikilink_text = convert_gfm_to_wikilinks(gfm_text)
    assert "[[システムアーキテクチャ]]" in wikilink_text
    assert "[[PID制御]]" in wikilink_text
