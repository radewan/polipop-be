from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.error_handlers import register_error_handlers
from src.users.router import router as users_router
from src.categories.router import router as categories_router
from src.products.router import router as products_router
from src.product_mutations.router import router as mutations_router
from src.config import settings

app = FastAPI(title="Polipop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # origin frontend, tidak boleh "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(categories_router, prefix="/categories", tags=["categories"])
app.include_router(products_router, prefix="/products", tags=["products"])
app.include_router(mutations_router, prefix="/mutations", tags=["mutations"])


@app.get("/health")
async def health():
    return {"status": "ok"}
