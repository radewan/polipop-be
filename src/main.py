from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.error_handlers import register_error_handlers
from src.users.router import router as users_router

app = FastAPI(title="Polipop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # origin frontend, tidak boleh "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(users_router, prefix="/users", tags=["users"])


@app.get("/health")
async def health():
    return {"status": "ok"}
