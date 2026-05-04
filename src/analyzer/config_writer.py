"""AI 解析結果を artists.yaml に書き戻す ConfigWriter。(参照: docs/basic-design.md § ConfigWriter)"""
from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.analyzer.site_analyzer import SiteConfig


def write_site_config(
    yaml_path: str | Path,
    artist_name: str,
    site_config: SiteConfig,
) -> None:
    """artists.yaml の該当アーティストに解析結果をマージして書き戻す。

    ``name`` / ``base_url`` は保持。``analyzed_at`` を今日の日付に更新。
    ``fetch`` / ``navigation`` / ``response`` / ``selectors`` / ``detail`` は
    解析結果で上書きする。

    書き込み中の例外でファイルが破損しないよう、同一ディレクトリに一時ファイルを
    書いてからアトミックにリネームする。

    Note:
        PyYAML の dump() によりコメントは消去される（仕様）。

    Args:
        yaml_path: artists.yaml のパス。
        artist_name: 更新対象アーティストの識別子（name フィールド）。
        site_config: AI が返したサイト設定。

    Raises:
        KeyError: 指定の artist_name が yaml_path に存在しない場合。
        yaml.YAMLError: YAML の読み書きに失敗した場合。
    """
    path = Path(yaml_path)
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    artists: list[dict[str, Any]] = data.get("artists") or []
    target = next((a for a in artists if a.get("name") == artist_name), None)
    if target is None:
        raise KeyError(f"アーティスト '{artist_name}' が {yaml_path} に見つかりません")

    target["analyzed_at"] = date.today().isoformat()

    for key, value in (
        ("fetch", site_config.fetch),
        ("navigation", site_config.navigation),
        ("response", site_config.response),
        ("selectors", site_config.selectors),
        ("detail", site_config.detail),
    ):
        if value:
            target[key] = value
        else:
            target.pop(key, None)

    dir_ = path.parent
    with tempfile.NamedTemporaryFile(
        "w", dir=dir_, suffix=".tmp", delete=False, encoding="utf-8"
    ) as tmp:
        yaml.dump(data, tmp, allow_unicode=True, default_flow_style=False, sort_keys=False)
        tmp_path = tmp.name

    os.replace(tmp_path, path)
