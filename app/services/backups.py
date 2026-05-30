import asyncio
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import BackupLog


async def run_pg_backup(settings: Settings, session: AsyncSession) -> None:
    Path("backups").mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = Path("backups") / f"nyx_garant_{stamp}.dump"
    if not settings.database_url.startswith("postgresql"):
        session.add(BackupLog(path=str(path), status="skipped", message="Unsupported DATABASE_URL for pg_dump"))
        await session.commit()
        return
    proc = await asyncio.create_subprocess_shell(
        f"pg_dump '{settings.database_url.replace('+asyncpg', '')}' -Fc -f '{path}'",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    session.add(BackupLog(path=str(path), status="ok" if proc.returncode == 0 else "error", message=stderr.decode()[:1000] or None))
    await session.commit()
