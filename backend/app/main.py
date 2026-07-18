"""Real Estate Proposal Engine — FastAPI entrypoint.

See spec §2 (overview) and §4 (workflows). Run with:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import all_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Real Estate Proposal Engine",
    description="Institutional-grade CRE brochure/PPTX/PDF generation from a live Building/Unit/Proposal data model.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in all_routers:
    app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
