from fastapi import FastAPI
from pymongo import MongoClient
from dotenv import dotenv_values
from routes import router as problem_router
from fastapi.middleware.cors import CORSMiddleware

import logging
import redis
import jwt
import uvicorn  # Add this import

config = dotenv_values(".env")

app = FastAPI()


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password, hashed_password):
    if plain_password == hashed_password:
        return True
    else:
        return False


@app.on_event("startup")
def startup_db_client():
    app.jwt = jwt
    app.JWT_SECRET_KEY = config["JWT_SECRET_KEY"]
    app.JWT_ALGORITHM = config["JWT_ALGORITHM"]
    app.ACCESS_TOKEN_EXPIRE_MINUTES = config["ACCESS_TOKEN_EXPIRE_MINUTES"]

    # MongoDB database
    app.mongodb_client = MongoClient(config["MONGO_URI"])
    app.database = app.mongodb_client[config["MONGO_DB"]]

    # Redis logs database
    app.redis_logs = redis.Redis(
        host=config["REDIS_HOST"], port=config["REDIS_PORT"], db=config["REDIS_DB_LOGS"])

    # Redis session database
    app.redis_session = redis.Redis(
        host=config["REDIS_HOST"], port=config["REDIS_PORT"], db=config["REDIS_DB_SESSION"])

    # logging
    logging.basicConfig(
        filename=config["LOG_FILE"], format='[customers] - [%(asctime)s] - [%(levelname)s] - %(message)s ', level=logging.DEBUG)
    app.logger = logging.getLogger(__name__)

    # password_context
    app.verify_password = verify_password


@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()


app.include_router(problem_router, tags=["customers"])


if __name__ == "__main__":
    uvicorn.run(app, port=9020)