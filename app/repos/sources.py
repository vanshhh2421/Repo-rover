from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from git import Repo

from app.core.settings import settings
from app.repos.registry import set_repo_root


def _safe_folder(repo_id: str) -> str:
    h = hashlib.sha256(repo_id.encode("utf-8")).hexdigest()[:16]
    return f"repo_{h}"


def resolve_repo_source(repo_id: str, source: str, branch: str | None = None) -> Path:
    p = Path(source)
    if p.exists() and p.is_dir():
        set_repo_root(repo_id, p)
        return p

    work = Path(settings.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    target = (work / _safe_folder(repo_id)).resolve()

    if target.exists():
        shutil.rmtree(target, ignore_errors=True)

    clone_kwargs = {}
    if branch:
        clone_kwargs["branch"] = branch

    Repo.clone_from(source, str(target), **clone_kwargs)
    set_repo_root(repo_id, target)
    return target
