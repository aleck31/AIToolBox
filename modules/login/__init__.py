from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from common.auth import cognito_auth
from common import USER_CONF
from common.chat_memory import chat_memory

# Create router
router = APIRouter()

# Setup templates
templates = Jinja2Templates(directory="modules/login")

# Dependency to get the current user
def get_user(request: Request):
    user = request.session.get('user')
    if user:
        return user.get('username')
    return None

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
        # Set user in USER_CONF
        USER_CONF.set_user(username)
        return RedirectResponse(url='/main', status_code=303)
    
    # If authentication fails, redirect back to login with error
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
        request.session.clear()
        if USER_CONF.username:
            USER_CONF.set_user(None)
        chat_memory.clear()
        return RedirectResponse(url='/login')
    except Exception as e:
        print(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")
