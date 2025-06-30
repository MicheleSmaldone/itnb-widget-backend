# src/snl_poc/api.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .crew import SnlPoc
from fastapi.responses import JSONResponse

app = FastAPI()

# Allow CORS for your frontend domain (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # or your deployed frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: str = ""

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        print(f"Received message: {req.message}")
        print(f"History: {req.history}")
        crew = SnlPoc()
        result = crew.chat(req.message, history=req.history)
        print(f"Result: {result}")
        return ChatResponse(response=result)
    except Exception as e:
        print(f"Error in chat_endpoint: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@app.get("/health")
async def health():
    return {"status": "ok"}