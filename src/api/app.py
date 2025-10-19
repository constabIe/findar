"""
FastAPI application factory.

Creates and configures the FastAPI application instance with all routers,
middleware, and exception handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.storage.dependencies import get_db_session


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Findar",
        description="Fraud Detection Service - Transaction analysis and suspicious activity detection",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check(get_db_session=get_db_session):
        """Health check endpoint for monitoring and load balancers."""
        return JSONResponse(
            content={
                "status": "ok",
                "service": "findar",
                "version": "0.1.0",
            }
        )

    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return JSONResponse(
            content={
                "service": "Findar - Fraud Detection Service",
                "version": "0.1.0",
                "docs": "/docs",
                "health": "/health",
            }
        )

    # Register API routers
    from src.modules.rule_engine.routes import router as rule_engine_router
    app.include_router(rule_engine_router, prefix="/api/v1", tags=["Rule Engine"])
    
    # TODO: Register additional API routers as they are implemented
    # from src.api.routes import transactions, statistics
    # app.include_router(transactions.router, prefix="/api/v1", tags=["Transactions"])
    # app.include_router(statistics.router, prefix="/api/v1", tags=["Statistics"])

    return app


# Create app instance
app = create_app()
