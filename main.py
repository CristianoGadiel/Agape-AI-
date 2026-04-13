from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Rota principal que FORÇA o carregamento do chat
@app.get("/")
async def read_index():
    return FileResponse('index.html')

# Se você tiver pastas de CSS ou JS, isso aqui ajuda
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/status")
async def get_status():
    return {"status": "Catedral Ágape Online"}
