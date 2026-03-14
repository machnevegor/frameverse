from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(
    title="Frameverse API",
    version="0.1.0",
    description="Backend service for Frameverse",
    docs_url="/api/docs",
    redoc_url=None,
)


@app.get("/api/scalar", include_in_schema=False)
async def scalar_ui() -> HTMLResponse:
    html = """
    <!doctype html>
    <html>
      <head>
        <title>Frameverse API — Scalar</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <script
          id="api-reference"
          data-url="/openapi.json"
          data-configuration='{"theme":"purple"}'
        ></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


class HealthResponse(BaseModel):
    status: str = "ok"


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse()
