"""
Custom server entry point with password authentication.

This wraps the ADK web server with a simple password gate.
Uses session-based auth stored in browser localStorage.
"""

import os
import secrets
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

# Load environment variables
load_dotenv()

# Get password from environment or Secret Manager
APP_PASSWORD = os.environ.get("APP_PASSWORD", "aimagna@2025")


# =============================================================================
# LOGIN PAGE HTML
# =============================================================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLL Data Integration - Login</title>
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
            <h1>🔐 LLL Data Integration</h1>
            <p>AI-Powered Schema Mapping System</p>
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
            window.location.href = '/dev-ui/';
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

# In-memory token store (simple for this use case)
# In production, use Redis or database
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
    
    EXCLUDED_PATHS = {"/", "/auth/login", "/auth/check", "/favicon.ico"}
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Allow excluded paths
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Check for auth token in header or query param
        token = request.headers.get("X-Auth-Token")
        if not token:
            token = request.query_params.get("token")
        if not token:
            # Check cookies
            token = request.cookies.get("auth_token")
        
        if token and validate_token(token):
            response = await call_next(request)
            return response
        
        # For API requests, return 401
        if path.startswith("/api") or request.headers.get("Accept") == "application/json":
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )
        
        # For web pages, redirect to login
        return HTMLResponse(
            content=f'<script>localStorage.removeItem("auth_token"); window.location.href="/";</script>',
            status_code=401
        )


# =============================================================================
# FASTAPI APP WITH AUTH
# =============================================================================

def create_app() -> FastAPI:
    """Create FastAPI app with auth wrapper around ADK."""
    
    # Import ADK app
    from google.adk.cli.fast_api import get_fast_api_app
    from . import agent
    
    # Create ADK app
    adk_app = get_fast_api_app(
        agent_dir="data_integration_agent",
        agents=[agent.root_agent],
        web=True,
        enable_trace_logging=False
    )
    
    # Create wrapper app
    app = FastAPI(title="LLL Data Integration Agent")
    
    # Add auth middleware
    app.add_middleware(AuthMiddleware)
    
    # Mount ADK app under /dev-ui
    # Note: ADK dev UI is served at root, we redirect
    
    @app.get("/", response_class=HTMLResponse)
    async def login_page():
        """Serve login page."""
        return LOGIN_HTML
    
    @app.post("/auth/login")
    async def login(request: Request, response: Response):
        """Handle login and return token."""
        body = await request.json()
        password = body.get("password", "")
        
        if password == APP_PASSWORD:
            token = generate_token()
            response.set_cookie(
                key="auth_token",
                value=token,
                httponly=False,  # Allow JS access for SPA
                samesite="lax",
                max_age=86400 * 7  # 7 days
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
    
    # Mount ADK routes - copy all routes from adk_app
    for route in adk_app.routes:
        if hasattr(route, 'path'):
            app.routes.append(route)
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
