import datetime
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from pid.api.deps import get_db
from pid.db import async_engine
from pid.models.route import Route

log = logging.getLogger("pid.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.connect() as conn:
        row = (await conn.execute(text("select current_database(), current_user, inet_server_addr(), inet_server_port()"))).one()
        log.info("DB connected: db=%s user=%s host=%s port=%s", *row)
    yield
    await async_engine.dispose()


app = FastAPI(title="PID API", lifespan=lifespan, root_path="/api")


@app.get("/")
async def hello() -> dict[str, str]:
    return {"message": "hello"}


@app.get("/routes")
async def list_routes(db: AsyncSession = Depends(get_db)) -> list[dict]:
    today = datetime.date.today()
    stmt = (
        select(Route)
        .where(Route.valid_from <= today)
        .where((Route.valid_until.is_(None)) | (Route.valid_until >= today))
        .order_by(Route.route_short_name)
    )
    result = await db.execute(stmt)
    return [
        {
            "route_id": r.route_id,
            "short_name": r.route_short_name,
            "long_name": r.route_long_name,
            "type": r.route_type.name if r.route_type else None,
        }
        for r in result.scalars()
    ]
