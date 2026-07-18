"""Real Estate Proposal Engine — FastAPI entrypoint.

See spec §2 (overview) and §4 (workflows). Run with:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_current_user
from app.database import init_db
from app.routers import all_routers
from app.routers import auth as auth_router


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

# /auth/login is the one endpoint that must work with no token yet; everything
# else requires a logged-in user (no per-route scoping — see app/auth.py).
app.include_router(auth_router.router)

for router in all_routers:
    app.include_router(router, dependencies=[Depends(get_current_user)])


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
