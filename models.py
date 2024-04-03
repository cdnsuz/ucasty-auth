import uuid
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union
from bson import ObjectId


class PersinalModel(BaseModel): 
    # all fields are optional
    first_name: Optional[str] = Field(...)
    last_name: Optional[str] = Field(...)
    address: Optional[str] = Field(...)
    city: Optional[str] = Field(...)
    country: Optional[str] = Field(...)
    zip_code: Optional[str] = Field(...)
    profile_picture: Optional[str] = Field(...)

class Customer(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    username: Optional[str] = Field(...) # TODO: add username to registration form
    email: Optional[str] = Field(...) # TODO: add email to registration form
    password: Optional[str] = Field(...) # TODO: hash password before storing
    phone_number: Optional[str] = Field(...)

    # personal info no Required fields
    # personal_info: Optional[PersinalModel] = Field(...) 
    personal_info: Optional[PersinalModel] = Field(default_factory=lambda: PersinalModel())
    
    @validator("id", pre=True, allow_reuse=True)
    def convert_to_str(cls, value):
        return str(value)
    
    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "username": "username",
                "email": "email",
                "password": "password",
                "phone_number": "phone_number",
                "personal_info": {
                    "first_name": "first_name",
                    "last_name": "last_name",
                    "address": "address",
                    "city": "city",
                    "country": "country",
                    "zip_code": "zip_code",
                    "profile_picture": "profile_picture"
                }
            }
        }

# Login model
class Login(BaseModel):
    # email required field not nullable
    email: str = Field(...)
    password: str = Field(...)



class Google(BaseModel):
    email: str = Field(...)  # Google email
    name: Optional[str] = Field(None)  # Full name of the user
    picture: Optional[str] = Field(None)  # URL to the user's profile picture
    given_name: Optional[str] = Field(None)
    family_name: Optional[str] = Field(None)

    # Add more fields as needed
    providerAccountId: Union[str] = Field(None)  # providerAccountId field


class GoogleGetToken(BaseModel):
    access_token: str = Field(...)  # Google email
    id_token: str = Field(...)  # Google email
    providerAccountId: str = Field(...)  # Google email


# register model
class Register(BaseModel):
    username: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)

class Token(BaseModel):
    access_token: str = None
    token_type: str = None


# All responses will have the following format
class ResponseModel(BaseModel):
    # data: dict = None # TODO: change to dict or list if null is not allowed in the response
    data: Union[dict, List[dict]] = None
    message: str = None

