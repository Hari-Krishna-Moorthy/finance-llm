from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .routes import ui

app = FastAPI(title="Finance LLM")

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include Routers
app.include_router(ui.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
