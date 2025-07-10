# src/snl_poc/api.py
import logging

# Silence all loggers by default
logging.getLogger().setLevel(logging.WARNING)

# Silence specific noisy libraries
for noisy_logger in [
    "httpx", "LiteLLM", "tools.groundx_tool", "uvicorn", "uvicorn.error", "uvicorn.access"  # Removed "mem0" since it's disabled
]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from crew import SnlPoc
from fastapi.responses import JSONResponse
import traceback

app = FastAPI()

# Allow CORS for your frontend domain (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "https://*.vercel.app",
        "https://your-frontend-app.vercel.app"  # Replace with your actual Vercel URL
    ],
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
        print(f"[API DEBUG] Received message: {req.message}")
        print(f"[API DEBUG] History: {req.history}")
        
        # Validate request
        if not req.message or not req.message.strip():
            print(f"[API DEBUG] Empty message received, returning error")
            return ChatResponse(response="Error: Please provide a valid message. Empty messages cannot be processed.")
        
        crew = SnlPoc()
        result = crew.chat(req.message, history=req.history)
        print(f"[API DEBUG] Result type: {type(result)}")
        print(f"[API DEBUG] Result length: {len(result)} chars")
        print(f"[API DEBUG] Result content: {result}")
        print(f"[API DEBUG] Contains PRIMARY_SOURCE marker: {'[PRIMARY_SOURCE:' in result}")
        return ChatResponse(response=result)
    except Exception as e:
        # print(f"[BACKEND DEBUG] Error in chat_endpoint: {e}")
        traceback.print_exc()  # <-- Add this line
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok"}