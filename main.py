from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
import uvicorn
import json
import logging

from config import settings
from database import init_db
from routers import (
    users_router,
    login_router,
    classes_router,
    functions_router,
    batch_router,
    coupon_router,
    config_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print(f"Server started on http://{settings.HOST}:{settings.PORT}")
    print(f"Parse endpoint: http://{settings.HOST}:{settings.PORT}/parse/")
    print(f"Application ID: {settings.APPLICATION_ID}")
    yield
    # Shutdown
    print("Server shutting down...")


app = FastAPI(
    title="Attack on Moe - Private Server",
    description="Parse-compatible backend server for Attack on Moe",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware to validate Application ID
@app.middleware("http")
async def validate_app_id(request: Request, call_next):
    # Skip validation for non-parse endpoints
    if not request.url.path.startswith("/parse"):
        return await call_next(request)

    # Get Application ID from header
    app_id = request.headers.get("X-Parse-Application-Id")

    # Allow requests without app ID for now (for testing)
    # In production, you might want to enforce this
    if app_id and app_id != settings.APPLICATION_ID:
        return JSONResponse(
            status_code=401,
            content={"code": 101, "error": "Invalid Application ID"}
        )

    return await call_next(request)


# Middleware to log request body
@app.middleware("http")
async def log_request_body(request: Request, call_next):
    # Only log for parse endpoints
    if request.url.path.startswith("/parse"):
        # Get request info
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""

        # Read request body
        body = b""
        if method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        # Log request
        log_msg = f"\n{'='*60}\n"
        log_msg += f"[REQUEST] {method} {path}"
        if query_params:
            log_msg += f"?{query_params}"
        log_msg += f"\n"

        # Log headers (selected)
        session_token = request.headers.get("X-Parse-Session-Token", "")
        if session_token:
            log_msg += f"[SESSION] {session_token[:20]}...\n"

        # Log body
        if body:
            try:
                body_json = json.loads(body.decode('utf-8'))
                # Pretty print JSON
                body_str = json.dumps(body_json, indent=2, ensure_ascii=False)
                log_msg += f"[BODY]\n{body_str}\n"
            except:
                log_msg += f"[BODY] {body.decode('utf-8', errors='ignore')}\n"

        log_msg += f"{'='*60}"
        logger.info(log_msg)

        # Reconstruct request with body for downstream handlers
        # We need to create a new receive function that returns the body we already read
        async def receive():
            return {"type": "http.request", "body": body}

        # Create a new request with the modified receive
        request = Request(request.scope, receive)

    response = await call_next(request)
    return response


# Include routers
app.include_router(config_router)
app.include_router(users_router)
app.include_router(login_router)
app.include_router(classes_router)
app.include_router(functions_router)
app.include_router(batch_router)
app.include_router(coupon_router)


@app.get("/")
async def root():
    return {
        "name": "Attack on Moe - Private Server",
        "version": "1.0.0",
        "parse_endpoint": "/parse/",
        "application_id": settings.APPLICATION_ID
    }


@app.get("/parse")
async def parse_root():
    return {"status": "ok"}


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
