"""
FastAPI application factory.

Creates and configures the FastAPI application instance with all routers,
middleware, and exception handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app


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

    # Register API routers
    from src.modules.rule_engine.routes import router as rule_engine_router

    app.include_router(rule_engine_router, prefix="/api/v1", tags=["Rule Engine"])

    # Register users router
    from src.modules.users.routes import router as users_router

    app.include_router(users_router, prefix="/api/v1", tags=["Users"])

    # Register user notifications router
    from src.modules.users.notifications_routes import (
        router as user_notifications_router,
    )

    app.include_router(user_notifications_router, prefix="/api/v1")

    # TODO: Register additional API routers as they are implemented
    # from src.api.routes import transactions, statistics
    # app.include_router(transactions.router, prefix="/api/v1", tags=["Transactions"])
    # Register API routers
    from src.modules.transactions import routes

    app.include_router(routes.router, prefix="/api/v1", tags=["Transactions"])

    # Register reporting router
    from src.modules.reporting.routes import router as reporting_router

    app.include_router(reporting_router, prefix="/api/v1", tags=["Reporting"])

    # Register ML module router
    from src.modules.ml.routes import router as ml_router

    app.include_router(ml_router, prefix="/api/v1", tags=["ML"])

    # Administrative notifications router is disabled - using user-level notifications only
    # from src.modules.notifications.routes import router as notifications_router
    # app.include_router(notifications_router, prefix="/api/v1", tags=["Notifications"])

    # Mount Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # TODO: Register additional routers
    # from src.api.routes import rules, statistics
    # app.include_router(rules.router, prefix="/api/v1", tags=["Rules"])
    # app.include_router(statistics.router, prefix="/api/v1", tags=["Statistics"])

    return app


# Create app instance
app = create_app()
