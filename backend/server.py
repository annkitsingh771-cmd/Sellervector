"""
AdPilot â€” Amazon PPC Campaign Manager
=====================================
Full backend (server.py)

Fixes applied from the broken original:
  * ends(get_current_user) -> Depends(get_current_user)
  * Completed the truncated /c... endpoint (now /campaign-builder/create)
  * Replaced plain-string user_id dependency with a proper User object
  * Added the missing auth layer, DB models and schemas everything was assuming

Added for the "make it a real tool" request:
  * JWT auth (register / login / me)
  * SQLAlchemy + SQLite persistence (swap DATABASE_URL for Postgres in prod)
  * Stores (connect / disconnect / list / sync)   <- fixes the "Connect Store" UX
  * Campaigns, Keywords CRUD
  * Automation Rules with 4 condition types (>, <, =, between)  <- matches UI colors
  * Daily Optimizations (list / toggle / apply-one / apply-all)
  * Analytics (dashboard KPIs, top keywords)
  * Notifications (list / mark-read / WebSocket)  <- fixes bell icon
  * Campaign Builder (products list + AI generation via Anthropic)
  * CORS, health check, error handlers
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import httpx
from fastapi import (
    FastAPI, APIRouter, Depends, HTTPException, status,
    WebSocket, WebSocketDisconnect, Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, field_validator

from sqlalchemy import (
    create_engine, Column, String, Float, Integer, Boolean,
    DateTime, Text, ForeignKey, desc,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# ==============================================================
#  CONFIG
# ==============================================================
SECRET_KEY = os.getenv("SECRET_KEY", "adpilot-dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./adpilot.db")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "*").split(",")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("adpilot")

# ==============================================================
#  DATABASE
# ==============================================================
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================
#  ORM MODELS
# ==============================================================
class User(Base):
    _tablename_ = "users"
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, default="")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    stores          = relationship("Store", back_populates="user", cascade="all, delete-orphan")
    notifications   = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Store(Base):
    _tablename_ = "stores"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    name         = Column(String, nullable=False)
    marketplace  = Column(String, default="us")
    seller_id    = Column(String, default="")
    api_token    = Column(String, default="")
    profile_id   = Column(String, default="")
    is_connected = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_sync    = Column(DateTime, nullable=True)
    user         = relationship("User", back_populates="stores")
    campaigns    = relationship("Campaign", back_populates="store", cascade="all, delete-orphan")


class Campaign(Base):
    _tablename_ = "campaigns"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id      = Column(String, ForeignKey("stores.id"), nullable=False)
    name          = Column(String, nullable=False)
    campaign_type = Column(String, default="SP")
    status        = Column(String, default="draft")
    daily_budget  = Column(Float, default=50.0)
    spend         = Column(Float, default=0.0)
    revenue       = Column(Float, default=0.0)
    impressions   = Column(Integer, default=0)
    clicks        = Column(Integer, default=0)
    orders        = Column(Integer, default=0)
    acos          = Column(Float, nullable=True)
    roas          = Column(Float, nullable=True)
    ctr           = Column(Float, nullable=True)
    cvr           = Column(Float, nullable=True)
    target_acos   = Column(Float, default=25.0)
    asin          = Column(String, default="")
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    store         = relationship("Store", back_populates="campaigns")
    keywords      = relationship("Keyword", back_populates="campaign", cascade="all, delete-orphan")


class Keyword(Base):
    _tablename_ = "keywords"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id  = Column(String, ForeignKey("campaigns.id"), nullable=False)
    keyword_text = Column(String, nullable=False)
    match_type   = Column(String, default="exact")
    bid          = Column(Float, default=1.0)
    status       = Column(String, default="active")
    clicks       = Column(Integer, default=0)
    impressions  = Column(Integer, default=0)
    spend        = Column(Float, default=0.0)
    orders       = Column(Integer, default=0)
    acos         = Column(Float, nullable=True)
    campaign     = relationship("Campaign", back_populates="keywords")


class AutomationRule(Base):
    _tablename_ = "automation_rules"
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id         = Column(String, ForeignKey("users.id"), nullable=False)
    name            = Column(String, nullable=False)
    description     = Column(Text, default="")
    metric          = Column(String, nullable=False)
    condition       = Column(String, nullable=False)
    threshold_value = Column(Float, nullable=True)
    threshold_min   = Column(Float, nullable=True)
    threshold_max   = Column(Float, nullable=True)
    action          = Column(String, nullable=False)
    action_value    = Column(Float, nullable=True)
    lookback_days   = Column(Integer, default=7)
    apply_to        = Column(String, default="all")
    is_active       = Column(Boolean, default=True)
    times_triggered = Column(Integer, default=0)
    last_triggered  = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


class DailyOptimization(Base):
    _tablename_ = "daily_optimizations"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    campaign_id  = Column(String, ForeignKey("campaigns.id"), nullable=True)
    keyword_id   = Column(String, ForeignKey("keywords.id"), nullable=True)
    title        = Column(String, nullable=False)
    description  = Column(Text, default="")
    action       = Column(String, nullable=False)
    action_value = Column(Float, nullable=True)
    status       = Column(String, default="pending")
    rule_id      = Column(String, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    applied_at   = Column(DateTime, nullable=True)


class Notification(Base):
    _tablename_ = "notifications"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    title      = Column(String, nullable=False)
    message    = Column(Text, nullable=False)
    severity   = Column(String, default="info")
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="notifications")


Base.metadata.create_all(bind=engine)


# ==============================================================
#  AUTH
# ==============================================================
pwd_max_bytes = 72  # bcrypt hard limit
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def hash_password(pw: str) -> str:
    pw_bytes = pw.encode("utf-8")[:pwd_max_bytes]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    plain_bytes = plain.encode("utf-8")[:pwd_max_bytes]
    try:
        return bcrypt.checkpw(plain_bytes, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """The fragment had ends(get_current_user) -- that was the bug. This is the real dependency."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise exc
    return user


# ==============================================================
#  PYDANTIC SCHEMAS
# ==============================================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = ""


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class StoreCreate(BaseModel):
    name: str
    marketplace: str = "us"
    seller_id: Optional[str] = ""
    api_token: Optional[str] = ""
    profile_id: Optional[str] = ""


class StoreOut(BaseModel):
    id: str
    name: str
    marketplace: str
    seller_id: str
    profile_id: str
    is_connected: bool
    connected_at: datetime
    last_sync: Optional[datetime]
    class Config:
        from_attributes = True


class CampaignCreate(BaseModel):
    store_id: str
    name: str
    campaign_type: str = "SP"
    daily_budget: float = 50.0
    target_acos: float = 25.0
    asin: Optional[str] = ""


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    daily_budget: Optional[float] = None
    target_acos: Optional[float] = None


class CampaignOut(BaseModel):
    id: str
    store_id: str
    name: str
    campaign_type: str
    status: str
    daily_budget: float
    spend: float
    revenue: float
    impressions: int
    clicks: int
    orders: int
    acos: Optional[float]
    roas: Optional[float]
    ctr: Optional[float]
    cvr: Optional[float]
    target_acos: float
    asin: str
    created_at: datetime
    class Config:
        from_attributes = True


class KeywordCreate(BaseModel):
    campaign_id: str
    keyword_text: str
    match_type: str = "exact"
    bid: float = 1.0


class KeywordUpdate(BaseModel):
    bid: Optional[float] = None
    status: Optional[str] = None


class KeywordOut(BaseModel):
    id: str
    campaign_id: str
    keyword_text: str
    match_type: str
    bid: float
    status: str
    clicks: int
    impressions: int
    spend: float
    orders: int
    acos: Optional[float]
    class Config:
        from_attributes = True


VALID_CONDITIONS = {"greater_than", "less_than", "equals", "between"}
VALID_METRICS    = {"acos", "roas", "clicks", "impressions", "spend", "orders", "ctr", "cvr"}
VALID_ACTIONS    = {"bid_up", "bid_down", "pause", "enable", "negate", "budget_up", "budget_down", "flag"}


class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    metric: str
    condition: str
    threshold_value: Optional[float] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    action: str
    action_value: Optional[float] = None
    lookback_days: int = 7
    apply_to: str = "all"

    @field_validator("condition")
    @classmethod
    def _cond(cls, v):
        if v not in VALID_CONDITIONS:
            raise ValueError(f"condition must be one of {VALID_CONDITIONS}")
        return v

    @field_validator("metric")
    @classmethod
    def _metric(cls, v):
        if v not in VALID_METRICS:
            raise ValueError(f"metric must be one of {VALID_METRICS}")
        return v

    @field_validator("action")
    @classmethod
    def _action(cls, v):
        if v not in VALID_ACTIONS:
            raise ValueError(f"action must be one of {VALID_ACTIONS}")
        return v


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    threshold_value: Optional[float] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    action_value: Optional[float] = None


class RuleOut(BaseModel):
    id: str
    name: str
    description: str
    metric: str
    condition: str
    threshold_value: Optional[float]
    threshold_min: Optional[float]
    threshold_max: Optional[float]
    action: str
    action_value: Optional[float]
    lookback_days: int
    apply_to: str
    is_active: bool
    times_triggered: int
    last_triggered: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True


class OptimizationOut(BaseModel):
    id: str
    campaign_id: Optional[str]
    keyword_id: Optional[str]
    title: str
    description: str
    action: str
    action_value: Optional[float]
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    is_read: bool
    created_at: datetime
    class Config:
        from_attributes = True


class AnalyticsOut(BaseModel):
    total_spend: float
    total_revenue: float
    avg_acos: Optional[float]
    active_campaigns: int
    paused_campaigns: int
    draft_campaigns: int
    total_impressions: int
    total_clicks: int
    total_orders: int
    avg_ctr: Optional[float]
    avg_cvr: Optional[float]
    roas: Optional[float]


# ==============================================================
#  WEBSOCKET NOTIFICATION HUB  (fixes the hard-coded "5" badge)
# ==============================================================
class NotificationHub:
    def _init_(self):
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: str, ws: WebSocket):
        if user_id in self.active:
            self.active[user_id] = [w for w in self.active[user_id] if w is not ws]
            if not self.active[user_id]:
                del self.active[user_id]

    async def push(self, user_id: str, payload: dict):
        for ws in list(self.active.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)


hub = NotificationHub()


async def create_notification(
    db: Session, user_id: str, title: str, message: str, severity: str = "info"
):
    n = Notification(user_id=user_id, title=title, message=message, severity=severity)
    db.add(n)
    db.commit()
    db.refresh(n)
    await hub.push(user_id, {
        "type": "notification",
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "severity": n.severity,
        "created_at": n.created_at.isoformat(),
    })
    return n


# ==============================================================
#  RULE ENGINE  (color-coded conditions match the UI)
# ==============================================================
def _metric_value(obj, metric: str) -> Optional[float]:
    return getattr(obj, metric, None)


def _condition_passes(rule: AutomationRule, value: Optional[float]) -> bool:
    if value is None:
        return False
    c = rule.condition
    if c == "greater_than" and rule.threshold_value is not None:
        return value > rule.threshold_value
    if c == "less_than" and rule.threshold_value is not None:
        return value < rule.threshold_value
    if c == "equals" and rule.threshold_value is not None:
        return abs(value - rule.threshold_value) < 1e-6
    if c == "between" and rule.threshold_min is not None and rule.threshold_max is not None:
        return rule.threshold_min <= value <= rule.threshold_max
    return False


async def run_rules_for_user(db: Session, user: User) -> List[DailyOptimization]:
    """Evaluate all active rules against campaigns + keywords, queue optimizations."""
    rules = db.query(AutomationRule).filter(
        AutomationRule.user_id == user.id, AutomationRule.is_active == True
    ).all()
    store_ids = [s.id for s in user.stores]
    campaigns = db.query(Campaign).filter(Campaign.store_id.in_(store_ids)).all()
    created: List[DailyOptimization] = []

    for rule in rules:
        targets = campaigns
        if rule.apply_to in ("SP", "SB", "SD"):
            targets = [c for c in campaigns if c.campaign_type == rule.apply_to]

        for camp in targets:
            val = _metric_value(camp, rule.metric)
            if _condition_passes(rule, val):
                opt = DailyOptimization(
                    user_id=user.id, campaign_id=camp.id,
                    title=f"{camp.name}",
                    description=f"{rule.name}: {rule.metric}={val} triggered rule",
                    action=rule.action, action_value=rule.action_value, rule_id=rule.id,
                )
                db.add(opt); created.append(opt)
                rule.times_triggered += 1
                rule.last_triggered = datetime.utcnow()

            for kw in camp.keywords:
                kval = _metric_value(kw, rule.metric)
                if _condition_passes(rule, kval):
                    opt = DailyOptimization(
                        user_id=user.id, campaign_id=camp.id, keyword_id=kw.id,
                        title=f"{camp.name} -- [{kw.keyword_text}]",
                        description=f"{rule.name}: {rule.metric}={kval} triggered rule",
                        action=rule.action, action_value=rule.action_value, rule_id=rule.id,
                    )
                    db.add(opt); created.append(opt)
                    rule.times_triggered += 1
                    rule.last_triggered = datetime.utcno
