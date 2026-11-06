from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, calls, cases, farmers, knowledge, marketplace, telephony
from app.config import get_settings
from app.database import Base, engine, migrate_compatible_schema
from app.database.session import SessionLocal
from app.services.seed import seed_demo_data

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_compatible_schema()
    with SessionLocal() as db:
        seed_demo_data(db)
    yield


app = FastAPI(
    title="RYTHU SAHAYA API",
    version="0.1.0",
    description=(
        "Telugu-first cotton crop problem-resolution MVP for Nalgonda district. "
        "All bundled agricultural records are demonstration data unless independently verified."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Case-Access-Token"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(farmers.router, prefix=settings.api_prefix)
app.include_router(calls.router, prefix=settings.api_prefix)
app.include_router(cases.router, prefix=settings.api_prefix)
app.include_router(knowledge.router, prefix=settings.api_prefix)
app.include_router(telephony.router, prefix=settings.api_prefix)
app.include_router(marketplace.router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": "rythu-sahaya-api", "mode": "demo-safe"}
