# app/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import init_orm, close_orm

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("START")
    await init_orm()
    yield
    await close_orm()
    print("FINISH")
