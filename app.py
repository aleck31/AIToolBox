# Copyright iX.
# SPDX-License-Identifier: MIT-0
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from modules.login import router as login_router, get_user
import gradio as gr
from common.llm_config import init_default_models
from common.config import get_config_value
from modules.main_ui import create_main_interface
from common.logger import logger


def initialize_app():
    """Initialize app configurations"""
    # Initialize default LLM models if none exist
    init_default_models()

# Get secret key from config or use default
DEFAULT_SECRET_KEY = "aibox-default-secret-key-do-not-use-in-production"
secret_key = get_config_value('SECRET_KEY', ['session', 'secret_key']) or DEFAULT_SECRET_KEY

# Create FastAPI app
app = FastAPI()

# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    session_cookie="session",
    max_age=7200,  # 2 hours
    same_site="lax",  # Prevents CSRF while allowing normal navigation
    https_only=False,  # Set to True in production with HTTPS
    path="/",  # Make cookie available for all paths    
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
        get_user(request)
        logger.debug("User found, redirecting to main")
        return RedirectResponse(url='/main')
    except HTTPException:
        logger.debug("No user found, redirecting to login")
        return RedirectResponse(url='/login')

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Create main interface
main_ui = create_main_interface()

# Mount Gradio app with auth_dependency
app = gr.mount_gradio_app(
    app, 
    main_ui, 
    path="/main",
    auth_dependency=get_user
)

if __name__ == "__main__":
    # Initialize app configurations
    initialize_app()
    uvicorn.run(
        app,
        host='127.0.0.1', 
        port=8886
    )
