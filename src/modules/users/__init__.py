"""
User management module for admin panel authentication.

This module provides user registration, authentication, and authorization
functionality for the fraud detection system's admin panel.
"""

from src.modules.users.routes import router

__all__ = ["router"]
