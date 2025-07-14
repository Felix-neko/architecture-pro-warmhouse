# main.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# отдаём страницу с встраиваемым React‑компонентом
@app.get("/docs2", response_class=FileResponse)
async def asyncapi_page():
    return FileResponse("templates/asyncapi.html", media_type="text/html")


# отдаём сам YAML-файл со спецификацией
@app.get("/asyncapi.yaml")
async def asyncapi_spec():
    return FileResponse("telemetry_service_async_api.yaml", media_type="text/yaml")


@app.get("/")
async def root():
    return {"msg": "Перейдите на /docs для просмотра AsyncAPI‑документации"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
