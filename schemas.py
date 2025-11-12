"""
Database Schemas for MANGESTIC CTF

Define MongoDB collection schemas using Pydantic models.
Each model name maps to a collection with the lowercase name.
- User -> "user"
- Challenge -> "challenge"
- Solve -> "solve"
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class User(BaseModel):
    username: str = Field(..., description="Unique handle shown on leaderboard")
    email: EmailStr
    password_hash: str = Field(..., description="SHA256 password hash with salt")
    bio: Optional[str] = Field(None, description="Short profile bio")
    avatar_url: Optional[str] = Field(None, description="Profile avatar URL")

class Challenge(BaseModel):
    title: str = Field(..., description="Challenge title")
    description: str = Field(..., description="Markdown/HTML safe description")
    flag_hash: str = Field(..., description="SHA256 hash of the flag value")
    points: int = Field(..., ge=0, description="Score awarded for solving")
    author: str = Field(..., description="Username of the contributor")
    tags: Optional[List[str]] = Field(default=None, description="Topic tags")
    is_active: bool = Field(default=True)

class Solve(BaseModel):
    challenge_id: str = Field(..., description="ObjectId of the challenge as string")
    username: str = Field(..., description="Solver username")
    points: int = Field(..., ge=0)
