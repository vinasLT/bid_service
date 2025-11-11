import uvicorn
from fastapi import FastAPI
from fastapi_problem.handler import new_exception_handler, add_exception_handler

from app.config import settings
from app.routers.v1.private import private_router

docs_url = "/docs" if settings.enable_docs else None
redoc_url = "/redoc"  if settings.enable_docs else None
openapi_url = "/openapi.json" if settings.enable_docs else None
app = FastAPI(
    root_path=settings.ROOT_PATH,
    title="Bid Service",
    description="Allow users to bid on auctions.",
    version="0.0.1",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

eh = new_exception_handler()
add_exception_handler(app, eh)

app.include_router(private_router)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)