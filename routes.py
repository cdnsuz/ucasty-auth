from models import Token, ResponseModel, Login, Register, Google, GoogleGetToken
from fastapi import APIRouter, Request, HTTPException, status, Depends
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from bson.json_util import dumps, loads 

import platform
import datetime
import json
from pydantic import BaseModel

router = APIRouter()


# Authentication routes
@router.post(
    "/register",
    response_description="Register a new customer",
    response_model=ResponseModel,
)
def register_customer(customer: Register, request: Request):
    try:
        if not customer.email == "" and not customer.password == "":
            customer_doc = request.app.database["customers"].find_one(
                {"email": customer.email})
            if customer_doc:
                return ResponseModel(data=[], message="Email already registered")
            else:
                customer_doc = request.app.database["customers"].insert_one(
                    customer.dict(by_alias=True)
                )

                # ACCESS_TOKEN_EXPIRE_MINUTES = 30
                return ResponseModel(
                    data=dict({"ok": True}),
                    message="Registration successful",
                )
        else:
            return ResponseModel(data=[], message="Invalid email and/or password")
    except Exception as e:
        request.app.logger.error(f"[Error: {e}] - [URL: {request.url.path}]")
        return ResponseModel(data=[], message="Invalid email and/or password")


# Login route returns a JWT token to be used in subsequent requests
@router.post(
    "/login",
    response_description="Login a customer and return a JWT token",
    response_model=ResponseModel,
)
def login_customer(customer: Login, request: Request):
    try:
        if not customer.email == "" and not customer.password == "":
            print(customer)
            customer_doc = request.app.database["customers"].find_one(
                {"email": customer.email}
            )
            if customer_doc and request.app.verify_password(
                customer.password, customer_doc["password"]
            ):
                # Convert ObjectId to string
                customer_id = str(customer_doc["_id"])
                tokin = request.app.jwt.encode(
                    {
                        "id": customer_id,
                        "email": customer.email,
                        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                        "iat": datetime.datetime.utcnow(),
                    },
                    request.app.JWT_SECRET_KEY,
                    algorithm=request.app.JWT_ALGORITHM,
                )

                # Session add to redis
                # session_add_to_redis(customer_id, tokin, "browser", request)
                return ResponseModel(
                    data=dict(Token(access_token=tokin, token_type="bearer")),
                    message="Login successful",
                )
            else:
                request.app.logger.info(
                    f"[Invalid email and/or password: {customer.email}] - [URL: {request.url.path}]")
                return ResponseModel(data=[], message="Invalid email and/or password")
        else:
            request.app.logger.info(
                f"[Invalid email and/or password: {customer.email}] - [URL: {request.url.path}]")
            return ResponseModel(data=[], message="Invalid email and/or password")
    except Exception as e:
        request.app.logger.error(f"[Error: {e}] - [URL: {request.url.path}]")
        return ResponseModel(data=[], message="Invalid email and/or password")


def device_info_set_redis_hash_key_value_pair(customer_id, token, request: Request):
    try:
        system_info = platform.uname()
        chrome_version = request.headers.get("Chrome-Version")

        system_info_dict = {
            "system": system_info.system,
            "node": system_info.node,
            "release": system_info.release,
            "version": system_info.version,
            "machine": system_info.machine,
            "processor": system_info.processor,
            "chrome_version": chrome_version if chrome_version else "Not found",
        }

        # Redis hash items count for the customer
        redis_item_count = request.app.redis_client.hlen(customer_id)

        timestamp = datetime.datetime.now().timestamp()

        item = {"token": token, "system_info": system_info_dict}

        # Convert the dictionary to a JSON string before storing in Redis
        item_json = json.dumps(item)

        # redis hash new item add
        request.app.redis_client.hset(customer_id, timestamp, item_json)

        # print(f"redis_item_count: {redis_item_count}")
        # print(f"redis_item: {item_json}")
        return True

    except Exception as e:
        print(f"Error setting device info: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# TODO This function will add the token to redis session database
# Redis data structure: Hash
# Redis key: customer_id
# Redis item:
# - key: user_id
# - items: token, { timestamp, device, etc }
def session_add_to_redis(customer_id, token, device, request: Request):
    try:
        timestamp = datetime.datetime.now().timestamp()
        item_value = {"timestamp": timestamp, "device": device}

        # Convert the dictionary to a JSON string before storing in Redis
        item_json = json.dumps(item_value)

        # redis hash new item add
        request.app.redis_session.hset(customer_id, token, item_json)
        print(f"redis_item: {item_json} - {customer_id} - {token}")
        return True
    except Exception as e:
        request.app.logger.error(f"[Error: {e}] - [URL: {request.url.path}]")
        return False


# Dependency to get the current user based on the provided token
async def get_current_user(request: Request):
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ""

        payload = request.app.jwt.decode(
            auth_token,
            request.app.JWT_SECRET_KEY,
            algorithms=[request.app.JWT_ALGORITHM],
        )
        if not payload:
            return False
        user_email = str(payload["email"])  # Ensure user_id is a string

        print(user_email)
        user = request.app.database["customers"].find_one(
            {"email": user_email},
            {"password": 0}
        )
        print(user)
        if user:
            return user
        else:
            return False

    except HTTPException as e:
        request.app.logger.error(f"[Error: {e}] - [URL: {request.url.path}]")
        return False  # Re-raise FastAPI's HTTPException to maintain response format

class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if not isinstance(value, ObjectId):
            raise TypeError("ObjectId required")
        return str(value)

class PersonalInfo(BaseModel):
    first_name: str
    last_name: str = ""
    address: str = ""
    city: str = ""
    country: str = ""
    zip_code: str = ""
    profile_picture: str = ""

class CurrentUser(BaseModel):
    _id: ObjectIdStr
    username: str
    email: str
    password: str
    phone_number: str
    personal_info: PersonalInfo
@router.get("/user", response_model=ResponseModel)
async def get_user(request: Request, current_user: CurrentUser = Depends(get_current_user)):

    if not current_user:
        return ResponseModel(data=[], message="User not found")
    else:

        current_user_dict = current_user
        current_user_dict["_id"] = str(current_user_dict["_id"])

        serialized_user = jsonable_encoder(current_user_dict, by_alias=True)
        return ResponseModel(data=serialized_user, message="User details")



# Google auth -- v1
@router.post(
    "/google",
    response_description="Google auth a customer and return a ",
    response_model=ResponseModel,
)
def google_auth_customer(customer: Google, request: Request):
    global customer_id
    try:
        if not customer.providerAccountId == "" and not customer.email == "":
            customer_google_auth = request.app.database["google_authentication"].find_one(
                {"email": customer.email}
            )

            customer_doc = request.app.database["customers"].find_one(
                {"email": customer.email}
            )

            if not customer_google_auth:
                customer_github_auth_insert = request.app.database["google_authentication"].insert_one(
                    customer.dict(by_alias=True)
                )
                customer_doc = request.app.database["customers"].insert_one({
                    "name": customer.name,
                    "email": customer.email,
                    "password": "",
                    "phone_number": "",
                    "personal_info": {
                        "first_name": customer.given_name,
                        "last_name": customer.family_name,
                        "address": "",
                        "city": "",
                        "country": "",
                        "zip_code": "",
                        "profile_picture": customer.picture
                    },
                })
                customer_id = str(customer_doc.inserted_id)

            if customer_doc:
                customer_id = str(customer_doc["_id"])
            return ResponseModel(
                data=dict({"ok": True}),
                message="Google authentication successful"
            )
        else:
            request.app.logger.info(
                f"[Invalid Google authentication: {customer}] - [URL: {request.url.path}]")
            return ResponseModel(data=[], message="Invalid Google authentication")
    except Exception as e:
        request.app.logger.error(f"[Error: {e}] - [URL: {request.url.path}]")
        return ResponseModel(data=[], message="Invalid Google authentication")


@router.post(
    "/google/token",
    response_description="Google auth a customer and return a ",
    response_model=ResponseModel,
)
def google_auth_customer_token(customer: GoogleGetToken, request: Request):
    global customer_id
    try:
        if not customer.access_token == "" and not customer.id_token == "" and not customer.providerAccountId == "":
            customer_google_auth = request.app.database["google_authentication"].find_one(
                {"providerAccountId": str(customer.providerAccountId)}
            )

            if not customer_google_auth:
                request.app.logger.info(
                    f"[Invalid Google Token authentication: {customer}] - [URL: {request.url.path}]")
                return ResponseModel(data=[], message="Invalid Google authentication")

            customer_id = str(customer_google_auth["_id"])


            tokin = request.app.jwt.encode(
                {
                    "id": customer_id,
                    "email": customer_google_auth["email"],
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                    "iat": datetime.datetime.utcnow(),
                },
                request.app.JWT_SECRET_KEY,
                algorithm=request.app.JWT_ALGORITHM,
            )
            # Session add to redis
            session_add_to_redis(customer_id, tokin, "google", request)

            return ResponseModel(
                data=dict(Token(access_token=tokin, token_type="bearer")),
                message="Login successful",
            )
        else:
            request.app.logger.info(
                f"[Invalid Google Token authentication: {customer}] - [URL: {request.url.path}]")
            return ResponseModel(data=[], message="Invalid Google authentication")
    except Exception as e:
        request.app.logger.error(f"[Error: {e}] - [URL: {request.url.path}]")
        return ResponseModel(data=[], message="Invalid Google authentication")
