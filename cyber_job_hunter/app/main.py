from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import create_tables
from app.routes.auth_routes import router as auth_router
from app.routes.pages import router as pages_router


BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="CyberRank", lifespan=lifespan)

# Static files
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
(static_dir / "css").mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

# Routes
app.include_router(auth_router)
app.include_router(pages_router)
