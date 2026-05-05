import os

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import User, create_tables, get_db

load_dotenv()

app = FastAPI(title="Auth App")

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Password hashing helpers
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


@app.on_event("startup")
def on_startup():
    """Create database tables on startup."""
    create_tables()


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect root to login page."""
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, success: str = None):
    """Render the login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "success": success,
    })


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, error: str = None):
    """Render the signup page."""
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "error": error,
    })


# ─── Auth Actions ─────────────────────────────────────────────────────────────

@app.post("/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle signup form submission."""
    # Validate passwords match
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match.",
        })

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "An account with this email already exists.",
        })

    # Create new user
    hashed_password = hash_password(password)
    new_user = User(
        full_name=full_name,
        email=email,
        password_hash=hashed_password,
    )
    db.add(new_user)
    db.commit()

    return RedirectResponse(url="/login?success=Account+created+successfully.+Please+log+in.", status_code=303)


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle login form submission."""
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password.",
        })

    # Successful login — redirect to a welcome page
    return RedirectResponse(url=f"/welcome?name={user.full_name}", status_code=303)


@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page(request: Request, name: str = "User"):
    """Simple welcome page after login."""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Welcome</title>
        <link rel="stylesheet" href="/static/css/login.css">
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-header">
                    <div class="logo-icon">👋</div>
                    <h1>Welcome, {name}!</h1>
                    <p class="subtitle">You have successfully logged in.</p>
                </div>
                <a href="/login" class="btn-primary" style="text-decoration:none;display:block;text-align:center;">Log Out</a>
            </div>
        </div>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
