import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from auth import store

router = APIRouter(prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Neispravan email")
        return v


@router.post("/register", status_code=201)
def register(body: Credentials):
    if not store.create_user(body.email, body.password):
        raise HTTPException(status_code=409, detail="Korisnik sa tim emailom već postoji")
    return {"email": body.email}
