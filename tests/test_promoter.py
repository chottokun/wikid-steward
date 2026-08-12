from pathlib import Path
import pytest
from wikid_steward.core.promoter import check_reviewed_status, promote_document


def test_check_reviewed_status_unreviewed(tmp_path: Path):
    md_file = tmp_path / "test.md"
    md_file.write_text(
        "---\nid: test\nstatus: unreviewed\n---\n# Content", encoding="utf-8"
    )

    assert check_reviewed_status(md_file) is False


def test_check_reviewed_status_reviewed(tmp_path: Path):
    md_file = tmp_path / "test.md"
    md_file.write_text(
        "---\nid: test\nstatus: Reviewed\n---\n# Content", encoding="utf-8"
    )

    assert check_reviewed_status(md_file) is True


def test_promote_document_flow(tmp_path: Path):
    # ディレクトリツリーの擬似作成
    base_dir = tmp_path
    raw_dir = base_dir / "_raw" / "projA"
    staging_dir = base_dir / "staging" / "projA"
    wiki_dir = base_dir / "wiki" / "projA"
    raw_sources_dir = base_dir / "raw_sources" / "projA"

    raw_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)
    wiki_dir.mkdir(parents=True)
    raw_sources_dir.mkdir(parents=True)

    # 原本ファイル
    raw_file = raw_dir / "doc1.pdf"
    raw_file.write_text("raw pdf binary")

    # Staging ノート & アセット
    staging_note = staging_dir / "proja_doc1.md"
    staging_note.write_text(
        "---\nid: proja_doc1\nstatus: reviewed\n---\n# Content",
        encoding="utf-8",
    )

    staging_assets = staging_dir / "assets" / "proja_doc1"
    staging_assets.mkdir(parents=True)
    (staging_assets / "fig1.png").write_text("fake image")

    # 昇格の実行
    promote_document(
        staging_note=staging_note,
        base_dir=base_dir,
        raw_relative_path=Path("projA/doc1.pdf"),
        commit_git=False,  # テスト用擬似Git環境
    )

    # 移動検証: staging からは消えていること
    assert not staging_note.exists()
    assert not staging_assets.exists()

    # 移動検証: wiki に移動していること
    wiki_note = wiki_dir / "proja_doc1.md"
    wiki_assets = wiki_dir / "assets" / "proja_doc1"
    assert wiki_note.exists()
    assert (wiki_assets / "fig1.png").exists()

    # 原本移動検証: raw_sources に移動していること
    assert not raw_file.exists()
    assert (raw_sources_dir / "doc1.pdf").exists()


def test_promote_document_backup_on_conflict(tmp_path: Path):
    base_dir = tmp_path
    staging_dir = base_dir / "staging" / "projA"
    wiki_dir = base_dir / "wiki" / "projA"

    staging_dir.mkdir(parents=True)
    wiki_dir.mkdir(parents=True)

    # 既に wiki 側に同名ファイルが存在
    existing_wiki_note = wiki_dir / "proja_doc1.md"
    existing_wiki_note.write_text("Old Human Edit Content", encoding="utf-8")

    # 新しい Staging ノート
    staging_note = staging_dir / "proja_doc1.md"
    staging_note.write_text(
        "---\nid: proja_doc1\nstatus: reviewed\n---\n# New Content",
        encoding="utf-8",
    )

    # 昇格実行
    promote_document(
        staging_note=staging_note,
        base_dir=base_dir,
        raw_relative_path=None,
        commit_git=False,
    )

    # バックアップファイル (.bak) が作成されていること
    bak_files = list(wiki_dir.glob("proja_doc1.md.*.bak"))
    assert len(bak_files) == 1
    assert bak_files[0].read_text(encoding="utf-8") == "Old Human Edit Content"

    # 新しいノートが配置されていること
    assert existing_wiki_note.read_text(encoding="utf-8").endswith(
        "# New Content"
    )
