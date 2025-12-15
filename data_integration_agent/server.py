"""
Custom server entry point with password authentication.

Simple password gate for the ADK web server.
"""

import os
import secrets
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

# Load environment variables
load_dotenv()

# Get password from environment
APP_PASSWORD = os.environ.get("APP_PASSWORD", "aimagna")

# Debug: Log password info on startup (masked for security)
print(f"🔐 APP_PASSWORD configured: {'✅ from env' if 'APP_PASSWORD' in os.environ else '⚠️ using default'} (length: {len(APP_PASSWORD)})")

# =============================================================================
# LOGIN PAGE HTML
# =============================================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIMagna: Multi Agent Data Integration Demo - Login</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 2.5rem;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            width: 100%;
            max-width: 400px;
        }
        .logo {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .logo h1 {
            font-size: 1.75rem;
            color: #1a1a2e;
            margin-bottom: 0.25rem;
        }
        .logo p {
            color: #6b7280;
            font-size: 0.9rem;
        }
        .form-group {
            margin-bottom: 1.25rem;
        }
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #374151;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 0.875rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .error {
            background: #fef2f2;
            color: #dc2626;
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: none;
            font-size: 0.9rem;
        }
        .error.show { display: block; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <h1>🔐 AIMagna</h1>
            <p>Multi Agent Data Integration Demo</p>
        </div>
        <div class="error" id="error">Invalid password. Please try again.</div>
        <form id="loginForm">
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" 
                       placeholder="Enter access password" required autofocus>
            </div>
            <button type="submit" class="btn">Access Dashboard</button>
        </form>
    </div>
    <script>
        // Check if already authenticated
        if (localStorage.getItem('auth_token')) {
            fetch('/auth/check', {
                headers: { 'X-Auth-Token': localStorage.getItem('auth_token') }
            }).then(r => r.json()).then(data => {
                if (data.authenticated) window.location.href = '/dev-ui/';
            });
        }
        
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const password = document.getElementById('password').value;
            const errorEl = document.getElementById('error');
            
            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('auth_token', data.token);
                    window.location.href = '/dev-ui/';
                } else {
                    errorEl.classList.add('show');
                }
            } catch (err) {
                errorEl.classList.add('show');
            }
        });
    </script>
</body>
</html>
"""

# =============================================================================
# AUTH TOKEN MANAGEMENT
# =============================================================================

valid_tokens: set = set()

def generate_token() -> str:
    """Generate a secure random token."""
    token = secrets.token_urlsafe(32)
    valid_tokens.add(token)
    return token

def validate_token(token: str) -> bool:
    """Check if token is valid."""
    return token in valid_tokens

# =============================================================================
# AUTH MIDDLEWARE
# =============================================================================

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to check authentication on all requests except login."""
    
    EXCLUDED_PATHS = {"/", "/auth/login", "/auth/check", "/favicon.ico", "/health"}
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Allow excluded paths
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Allow all /dev-ui routes (ADK app handles its own auth if needed)
        if path.startswith("/dev-ui"):
            return await call_next(request)
        
        # Check for auth token
        token = request.headers.get("X-Auth-Token")
        if not token:
            token = request.query_params.get("token")
        if not token:
            token = request.cookies.get("auth_token")
        
        if token and validate_token(token):
            return await call_next(request)
        
        # For API requests, return 401
        if path.startswith("/api") or request.headers.get("Accept") == "application/json":
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        
        # For web pages, redirect to login
        return HTMLResponse(
            content='<script>localStorage.removeItem("auth_token"); window.location.href="/";</script>',
            status_code=401
        )

# =============================================================================
# MOUNT ADK APP ON STARTUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - replaces deprecated on_event."""
    # Startup
    try:
        from google.adk.cli.fast_api import get_fast_api_app
        
        # Import session service for persistent sessions
        try:
            from session_config import get_session_service
            session_service = get_session_service()
        except ImportError:
            print("⚠️ session_config not found, using default session service")
            session_service = None
        except Exception as e:
            print(f"⚠️ Failed to initialize session service: {e}")
            session_service = None
        
        # agents_dir should be the parent directory containing agent folders
        # Structure: /app/data_integration_agent/agent.py (with root_agent)
        adk_app_kwargs = {
            "agents_dir": "/app",
            "web": True,
            "url_prefix": "/dev-ui"
        }
        
        # Add session_service if available
        if session_service is not None:
            adk_app_kwargs["session_service"] = session_service
            print("✅ ADK app configured with persistent session service")
        
        adk_app = get_fast_api_app(**adk_app_kwargs)
        
        # Mount ADK under /dev-ui prefix
        app.mount("/dev-ui", adk_app)
        print("✅ ADK app mounted at /dev-ui")
        
    except Exception as e:
        print(f"⚠️ Could not mount ADK: {e}")
        import traceback
        traceback.print_exc()
    
    yield
    # Shutdown (if needed)

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(title="AIMagna: Multi Agent Data Integration Demo", lifespan=lifespan)

# Add auth middleware
app.add_middleware(AuthMiddleware)

@app.get("/", response_class=HTMLResponse)
async def login_page():
    """Serve login page."""
    return LOGIN_HTML

@app.get("/dev-ui")
async def dev_ui_redirect():
    """Redirect /dev-ui (no trailing slash) to /dev-ui/ for the mounted ADK app."""
    return RedirectResponse(url="/dev-ui/", status_code=302)

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/auth/login")
async def login(request: Request, response: Response):
    """Handle login and return token."""
    body = await request.json()
    password = body.get("password", "")
    
    # Debug logging
    print(f"🔍 Login attempt - received: '{password}' (len={len(password)}), expected: (len={len(APP_PASSWORD)}), match={password == APP_PASSWORD}")
    
    if password == APP_PASSWORD:
        token = generate_token()
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=False,
            samesite="lax",
            max_age=86400 * 7
        )
        return {"token": token, "status": "ok"}
    
    raise HTTPException(status_code=401, detail="Invalid password")

@app.get("/auth/check")
async def check_auth(request: Request):
    """Check if current token is valid."""
    token = request.headers.get("X-Auth-Token")
    if not token:
        token = request.cookies.get("auth_token")
    
    if token and validate_token(token):
        return {"authenticated": True}
    return {"authenticated": False}

@app.get("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout and invalidate token."""
    token = request.cookies.get("auth_token")
    if token and token in valid_tokens:
        valid_tokens.discard(token)
    response.delete_cookie("auth_token")
    return {"status": "logged out"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
