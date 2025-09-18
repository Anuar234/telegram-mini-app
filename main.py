from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print("🚀 FastAPI server is starting up...")

# Serve static files (CSS, images, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/product", response_class=HTMLResponse)
async def product(request: Request):
    return templates.TemplateResponse("product.html", {"request": request})

@app.get("/trainings", response_class=HTMLResponse)
async def trainings(request: Request):
    return templates.TemplateResponse("trainings.html", {"request": request})

@app.get("/support", response_class=HTMLResponse)
async def support(request: Request):
    return templates.TemplateResponse("support.html", {"request": request})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
