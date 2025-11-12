import os
import hashlib
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User as UserSchema, Challenge as ChallengeSchema, Solve as SolveSchema

app = FastAPI(title="MANGESTIC CTF API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class SubmitChallengeRequest(BaseModel):
    title: str
    description: str
    flag: str
    points: int
    tags: Optional[List[str]] = None

class SubmitFlagRequest(BaseModel):
    challenge_id: str
    flag: str


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@app.get("/")
def read_root():
    return {"name": "MANGESTIC CTF", "status": "ok"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Auth endpoints (simple demo: store hash, return basic status)
@app.post("/api/register")
def register(payload: RegisterRequest):
    # uniqueness check
    existing = db["user"].find_one({"$or": [{"username": payload.username}, {"email": payload.email}]})
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = UserSchema(
        username=payload.username,
        email=payload.email,
        password_hash=sha256(payload.password),
        bio=None,
        avatar_url=None,
    )
    user_id = create_document("user", user)
    return {"ok": True, "user_id": user_id}


@app.post("/api/login")
def login(payload: LoginRequest):
    hashed = sha256(payload.password)
    user = db["user"].find_one({"username": payload.username, "password_hash": hashed})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"ok": True, "username": user.get("username")}


# Challenge contribution
@app.post("/api/challenges")
def contribute_challenge(payload: SubmitChallengeRequest):
    ch = ChallengeSchema(
        title=payload.title,
        description=payload.description,
        flag_hash=sha256(payload.flag),
        points=payload.points,
        author="anonymous",
        tags=payload.tags,
        is_active=True,
    )
    ch_id = create_document("challenge", ch)
    return {"ok": True, "challenge_id": ch_id}


@app.get("/api/challenges")
def list_challenges():
    items = get_documents("challenge", {"is_active": True}, limit=100)
    for it in items:
        it["_id"] = str(it["_id"])
        it.pop("flag_hash", None)
    return {"ok": True, "items": items}


# Flag submission and leaderboard
@app.post("/api/submit-flag")
def submit_flag(payload: SubmitFlagRequest):
    # find challenge
    try:
        ch = db["challenge"].find_one({"_id": ObjectId(payload.challenge_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid challenge id")

    if not ch or not ch.get("is_active", True):
        raise HTTPException(status_code=404, detail="Challenge not found")

    if sha256(payload.flag) != ch.get("flag_hash"):
        raise HTTPException(status_code=400, detail="Incorrect flag")

    # add solve
    solve = SolveSchema(challenge_id=str(ch["_id"]), username="anonymous", points=ch.get("points", 0))
    _ = create_document("solve", solve)

    return {"ok": True, "message": "Flag accepted"}


@app.get("/api/leaderboard")
def leaderboard():
    pipeline = [
        {"$group": {"_id": "$username", "score": {"$sum": "$points"}}},
        {"$sort": {"score": -1}},
        {"$limit": 50},
    ]
    rows = list(db["solve"].aggregate(pipeline))
    items = [{"username": r["_id"], "score": r["score"]} for r in rows]
    return {"ok": True, "items": items}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
