from fastapi import FastAPI
from app.routers import feishu

app = FastAPI(title="OpenJarvis")

app.include_router(feishu.router, prefix="/webhook", tags=["feishu"])


@app.get("/")
async def root():
    return {"status": "ok"}

