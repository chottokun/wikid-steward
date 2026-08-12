from datetime import datetime, timezone
from pathlib import Path
import shutil
import yaml


def check_reviewed_status(file_path: Path | str) -> bool:
    """Markdown ファイルの先頭の YAML ヘッダーの status が 'reviewed' であるか判定する。

    Args:
        file_path: Markdown ファイルのパス

    Returns:
        reviewed の場合 True、それ以外は False
    """
    path = Path(file_path)
    if not path.exists():
        return False

    try:
        content = path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_data = yaml.safe_load(parts[1])
                if isinstance(yaml_data, dict):
                    status = yaml_data.get("status", "")
                    if (
                        isinstance(status, str)
                        and status.strip().lower() == "reviewed"
                    ):
                        return True
    except Exception:
        pass

    return False


def promote_document(
    staging_note: Path | str,
    base_dir: Path | str,
    raw_relative_path: Path | str | None = None,
    commit_git: bool = True,
) -> None:
    """staging/ から wiki/ への昇格、同名ファイルの .bak 非破壊退避、および原本の raw_sources/ への移動を実行する。

    Args:
        staging_note: staging 内の Markdown ファイルのパス
        base_dir: リポジトリのベースディレクトリ (例: Project/wikid-steward)
        raw_relative_path: _raw ディレクトリ内の原本の相対パス (例: "projA/doc1.pdf")
        commit_git: GitPython でセマンティックコミットを実行するかどうか
    """
    note_path = Path(staging_note)
    base = Path(base_dir)

    # staging/ からの相対パス階層を取得
    staging_base = base / "staging"
    rel_path = note_path.relative_to(staging_base)

    # ターゲットパス (wiki/ 内)
    wiki_base = base / "wiki"
    target_note = wiki_base / rel_path

    # アセットフォルダパスの特定 (Frontmatter の id または stem から取得)
    slug = note_path.stem
    try:
        content = note_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                meta = yaml.safe_load(parts[1]) or {}
                if "id" in meta:
                    slug = meta["id"]
    except Exception:
        pass

    staging_assets = note_path.parent / "assets" / slug
    if not staging_assets.exists():
        # 代替サーチ: staging 配下の assets から slug に合致するディレクトリを検索
        for possible_asset in note_path.parent.glob(f"**/assets/{slug}"):
            if possible_asset.is_dir():
                staging_assets = possible_asset
                break

    target_assets = target_note.parent / "assets" / slug

    # ターゲットディレクトリの準備
    target_note.parent.mkdir(parents=True, exist_ok=True)
    if staging_assets.exists():
        target_assets.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    # 1. 競合退避 (.bak) - Markdown ノート
    if target_note.exists():
        backup_note = target_note.parent / f"{target_note.name}.{timestamp}.bak"
        shutil.move(target_note, backup_note)

    # 2. 競合退避 (.bak) - アセットフォルダ
    if target_assets.exists():
        backup_assets = (
            target_assets.parent / f"{target_assets.name}.{timestamp}.bak"
        )
        shutil.move(target_assets, backup_assets)

    # 3. 物理移動: staging/ -> wiki/ (Markdown)
    shutil.move(note_path, target_note)

    # 用語自動抽出 & WikiLink バインドフック
    try:
        from wikid_steward.core.glossary import GlossaryExtractor
        from wikid_steward.core.relinker import WikiRelinker

        content = target_note.read_text(encoding="utf-8")
        extractor = GlossaryExtractor()
        terms = extractor.extract_terms(content)

        glossary_dir = wiki_base / "glossary"
        for term in terms:
            extractor.create_glossary_note(term, glossary_dir)

        relinker = WikiRelinker()
        relinked_content, _ = relinker.relink_text(content, terms)
        target_note.write_text(relinked_content, encoding="utf-8")
    except Exception as e:
        print(f"Glossary / Relinker promotion hook warning: {e}")

    # 4. 物理移動: staging/ -> wiki/ (Assets)
    if staging_assets.exists():
        shutil.move(staging_assets, target_assets)

    # 5. 原本バイナリの退避: _raw/ -> raw_sources/
    if raw_relative_path:
        raw_source = base / "_raw" / raw_relative_path
        target_raw_source = base / "raw_sources" / raw_relative_path
        if raw_source.exists():
            target_raw_source.parent.mkdir(parents=True, exist_ok=True)
            if target_raw_source.exists():
                backup_raw = (
                    target_raw_source.parent
                    / f"{target_raw_source.name}.{timestamp}.bak"
                )
                shutil.move(target_raw_source, backup_raw)
            shutil.move(raw_source, target_raw_source)

    # 6. セマンティック Git コミット
    if commit_git:
        try:
            from git import Repo

            repo = Repo(base)
            repo.index.add([str(target_note)])
            if target_assets.exists():
                repo.index.add([str(target_assets)])
            repo.index.commit(f"docs(wiki): promote reviewed note {rel_path}")
        except Exception:
            pass
