# api.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Tavus Avatar API")

class HealthResponse(BaseModel):
    status: str

@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}

@app.post("/start-avatar")
def start_avatar():
    """
    Frontend can call this later
    (token generation, room logic, etc.)
    """
    return {"message": "Avatar worker already running"}
