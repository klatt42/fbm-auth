"""Optional middleware helpers for CORS and rate limiting."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors(
    app: FastAPI,
    origins: list[str] | None = None,
    allow_credentials: bool = True,
) -> None:
    """Add CORS middleware with sensible defaults.

    Each tool should call this with its own allowed origins.
    """
    if origins is None:
        origins = [
            "http://localhost:3000",
            "http://localhost:3008",
            "http://localhost:5173",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
