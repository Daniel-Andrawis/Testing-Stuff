import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import create_tables
from app.routes.auth_routes import router as auth_router
from app.routes.pages import router as pages_router
from app.routes.api import router as api_router


BASE_DIR = Path(__file__).resolve().parent.parent


async def scheduled_scrape():
    """Background task: scrape all sources every 4 hours.
    Waits 30 seconds after startup before first run to not block boot."""
    from app.services.scheduler import run_all_scrapers
    await asyncio.sleep(30)  # let the server fully start first
    while True:
        try:
            # Run scrapers in thread pool since they use synchronous requests
            await asyncio.get_event_loop().run_in_executor(None, _sync_scrape)
        except Exception as e:
            print(f"[scheduler] Error: {e}")
        await asyncio.sleep(4 * 60 * 60)  # 4 hours


def _sync_scrape():
    """Wrapper to run async scraper from sync context in thread pool."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        from app.services.scheduler import run_all_scrapers
        loop.run_until_complete(run_all_scrapers())
    finally:
        loop.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    task = asyncio.create_task(scheduled_scrape())
    yield
    task.cancel()


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
app.include_router(api_router)
