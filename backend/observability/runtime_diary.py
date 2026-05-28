from __future__ import annotations

from typing import Optional

from repositories.runtime_diary_repo import RuntimeDiaryRepo


class RuntimeDiary:
    def __init__(self, repo: RuntimeDiaryRepo) -> None:
        self._repo = repo

    async def log(
        self,
        source: str,
        event: str,
        detail: str,
        session_id: Optional[str] = None,
    ) -> None:
        await self._repo.log(source, event, detail, session_id)
