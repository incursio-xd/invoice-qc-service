from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from contextlib import asynccontextmanager

from .routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Invoice QC Service starting up...")
    print("API documentation available at http://localhost:8000/docs")
    print("Frontend available at http://localhost:8000/")
    yield
    # Shutdown
    print("Invoice QC Service shutting down...")

app = FastAPI(
    title="Invoice QC Service",
    version="1.0.0",
    description="Invoice Extraction and Quality Control System",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Get frontend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Serve frontend
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    
    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        """Serve the frontend HTML page."""
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend not found. API is running at /docs"}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)