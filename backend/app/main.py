"""FastAPI application factory and same-origin frontend serving."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app import __version__
from backend.app.routers.health import router as health_router


def frontend_directory() -> Path:
    """Return the Vite production-output directory."""

    return Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    """Build an application instance suitable for production and tests."""

    application = FastAPI(
        title="Mac VLC Remote",
        version=__version__,
        description="Local, mobile-first control service for VLC on macOS.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    application.include_router(health_router, prefix="/api/v1")

    static_directory = frontend_directory()
    if (static_directory / "index.html").is_file():
        application.mount(
            "/",
            StaticFiles(directory=static_directory, html=True),
            name="frontend",
        )
    else:

        @application.get("/", include_in_schema=False)
        async def frontend_not_built() -> HTMLResponse:
            return HTMLResponse(
                """
                <!doctype html>
                <html lang="en">
                  <head><meta charset="utf-8"><title>Mac VLC Remote</title></head>
                  <body>
                    <main>
                      <h1>Frontend not built</h1>
                      <p>
                        Run <code>npm run build</code> or use
                        <code>make dev</code>.
                      </p>
                    </main>
                  </body>
                </html>
                """.strip()
            )

    return application


app = create_app()
