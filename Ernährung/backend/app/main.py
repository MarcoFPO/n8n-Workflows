from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os

from .core.config import settings
from .database.connection import engine, Base
from .routers import users, health, recipes, inventory, shopping, analytics, receipts

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Ernährungs-App",
    version="1.0.0",
    description="Umfassende Webanwendung für Ernährungsmanagement mit ML-basierten Rezeptempfehlungen"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(recipes.router, prefix="/api/v1", tags=["recipes"])
app.include_router(inventory.router, prefix="/api/v1", tags=["inventory"])
app.include_router(shopping.router, prefix="/api/v1", tags=["shopping"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(receipts.router, prefix="/api/v1", tags=["receipts"])

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main page redirect to frontend"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ernährungs-App</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="text-center">
                <h1>🥗 Ernährungs-App</h1>
                <p class="lead">Umfassende Webanwendung für Ernährungsmanagement</p>
                <div class="row mt-4">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">📊 Dashboard</h5>
                                <p class="card-text">Tägliche Rezeptvorschläge und Gesundheitstrends</p>
                                <a href="/dashboard" class="btn btn-primary">Dashboard öffnen</a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">📚 API Dokumentation</h5>
                                <p class="card-text">Vollständige API-Referenz</p>
                                <a href="/docs" class="btn btn-outline-primary">API Docs</a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">🔍 API Explorer</h5>
                                <p class="card-text">Interaktive API-Tests</p>
                                <a href="/redoc" class="btn btn-outline-secondary">ReDoc</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": "ernaehrungs-app", "version": "1.0.0"}