# Copyright iX.
# SPDX-License-Identifier: MIT-0
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import gradio as gr

from core.config import app_config  # Fixed import path
from llm.model_manager import model_manager
from common.login import router as login_router, get_auth_user
from common.main_ui import create_main_interface
from core.logger import logger

# Get configurations from app_config
server_config = app_config.server_config
security_config = app_config.security_config
cors_config = app_config.cors_config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app"""
    try:
        # Startup
        logger.info("Initializing application...")
        # Initialize default LLM models if none exist
        model_manager.init_default_models()
        logger.info("Application initialization complete")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")

# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=security_config['secret_key'],
    session_cookie="session",
    max_age=None,  # Let Cognito handle token expiration
    same_site="lax",  # Prevents CSRF while allowing normal navigation
    https_only=security_config['ssl_enabled'],  # Enable for production with HTTPS
    path="/",  # Make cookie available for all paths    
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config['allow_origins'],
    allow_credentials=True,
    allow_methods=cors_config['allow_methods'],
    allow_headers=cors_config['allow_headers'],
    expose_headers=["*"],
    max_age=3600,
)

# Include login routes
app.include_router(login_router)

@app.get('/')
def public(request: Request):
    """Root route handler"""
    logger.debug("Accessing root path")
    try:
        get_auth_user(request)
        logger.debug("User found, redirecting to main")
        return RedirectResponse(url='/main')
    except HTTPException:
        logger.debug("No user found, redirecting to login")
        return RedirectResponse(url='/login')

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Create main interface
main_ui = create_main_interface()

# Mount Gradio app with auth_dependency
app = gr.mount_gradio_app(
    app, 
    main_ui, 
    path="/main",
    auth_dependency=get_auth_user
)

if __name__ == "__main__":
    # Start server with configuration from app_config
    uvicorn.run(
        app,
        host=server_config['host'],
        port=server_config['port'],
        log_level=server_config['log_level']
    )
