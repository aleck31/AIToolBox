from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from core.auth import cognito_auth
from core.logger import logger
import json
from datetime import datetime


# Create router
router = APIRouter()

# Setup templates
templates = Jinja2Templates(directory="modules/login")


def log_unauth_access(request: Request, details: str = None):
    """Log unauthorized access attempts with detailed information"""
    # Get client IP - check for proxy headers first
    client_ip = request.headers.get('x-forwarded-for') or request.headers.get('x-real-ip') or request.client.host
    
    # Build security log entry
    security_log = {
        'client_ip': client_ip,
        'method': request.method,
        'request_url': str(request.url),
        'user_agent': request.headers.get('user-agent'),
        'details': details,
    }
    
    # Log as JSON for better parsing
    logger.warning(f"SECURITY_ALERT: Unauthorized access - {json.dumps(security_log, indent=2)}")


# Dependency to get the current user or raises exception
def get_user(request: Request):
    """Get current user from session"""
    # Log full session data at DEBUG level
    # logger.debug(f"Full request session data: {dict(request.session)}")
    
    user = request.session.get('user')
    
    if not user:
        # Log unauthorized access attempt
        log_unauth_access(
            request=request,
            details='Attempted to access protected route without valid session'
        )
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    username = user.get('username')
    logger.debug(f"Username extracted from session: {username}")
    # Log access token for debugging
    access_token = user.get('access_token')
    logger.debug(f"Access token verified: {bool(access_token)}")
    
    return username


@router.get('/login')
async def login_page(request: Request, error: str = None):
    """Render login page"""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )

@router.post('/auth')
async def auth(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handle authentication"""
    auth_result = cognito_auth.authenticate(username, password)
    if auth_result['success']:
        # Store user info and token in session
        request.session['user'] = {
            'username': username,
            'access_token': auth_result['tokens']['AccessToken']
        }
        logger.debug(f"Authentication successful. Session data: {dict(request.session)}")
        
        # Create response with redirect
        response = RedirectResponse(url='/main', status_code=303)
        return response
    
    # Log failed authentication attempt
    log_unauth_access(
        request=request,
        details=f'Failed authentication attempt for user: {username}'
    )
    
    # Redirect back to login with error
    return RedirectResponse(
        url=f'/login?error=Invalid username or password',
        status_code=303
    )

@router.get('/logout')
async def logout(request: Request):
    """Handle logout request"""
    try:
        user = request.session.get('user')
        if user and user.get('access_token'):
            cognito_auth.logout(user['access_token'])
        logger.debug(f"Session data before clear: {dict(request.session)}")
        request.session.clear()
        logger.debug("Session cleared during logout")
        
        # Create response with redirect
        response = RedirectResponse(url='/login')
        return response
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")
