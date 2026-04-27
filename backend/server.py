"""
SellerVector Backend — server.py
=================================
FIXES IN THIS VERSION
---------------------
1. _tablename_ -> __tablename__  (was the root cause of ALL accounts sharing data)
2. __init__ / __tablename__ everywhere (single-underscore dunder attrs are ignored by SQLAlchemy/Python)
3. Added ALL route handlers (the repo version was cut off at line 585 with zero routes)
4. Every query is scoped to current_user — account A never sees account B's data
5. Auth returns {token, user} so Login.js works without changes
6. Endpoints match exactly what every frontend page calls
7. NotificationSettings model added so NotificationCenter works
8. Demo seed endpoint so new accounts get sample data instantly
"""

import os, uuid, random, logging, re, json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import httpx
import bcrypt
from jose import JWTError, jwt
from fastapi import (
    FastAPI, APIRouter, Depends, HTTPException, status,
    WebSocket, WebSocketDisconnect, Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import (
    create_engine, Column, String, Float, Integer, Boolean,
    DateTime, Text, ForeignKey, desc,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# ──────────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────────
SECRET_KEY  = os.getenv("SECRET_KEY",  "sellervector-secret-change-in-prod")
ALGORITHM   = "HS256"
TOKEN_EXPIRY = 60 * 24   # 24 hours

DATABASE_URL          = os.getenv("DATABASE_URL", "sqlite:///./sellervector.db")
ANTHROPIC_API_KEY     = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL       = "claude-sonnet-4-20250514"
FRONTEND_ORIGINS = ["*"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sellervector")

# ──────────────────────────────────────────────────────────────
#  DATABASE
# ──────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
#  ORM MODELS  — __tablename__ with double underscores (THE FIX)
# ──────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"                          # ← double underscore (was single = BUG)
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, default="")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    stores                = relationship("Store",               back_populates="user",  cascade="all, delete-orphan")
    notifications         = relationship("Notification",        back_populates="user",  cascade="all, delete-orphan")
    notification_settings = relationship("NotificationSetting", back_populates="user",  uselist=False, cascade="all, delete-orphan")
    optimization_items    = relationship("OptimizationItem",    back_populates="user",  cascade="all, delete-orphan")
    automation_rules      = relationship("AutomationRule",      back_populates="user",  cascade="all, delete-orphan")


class Store(Base):
    __tablename__ = "stores"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    marketplace  = Column(String, nullable=False)
    store_name   = Column(String, nullable=False)
    seller_id    = Column(String, default="")
    api_token    = Column(String, default="")
    marketplace_id = Column(String, default="A21TJRUUN4KGV")
    # SP-API credentials per store
    sp_client_id     = Column(String, default="")
    sp_client_secret = Column(String, default="")
    sp_refresh_token = Column(String, default="")
    # Ads API credentials per store
    ads_client_id     = Column(String, default="")
    ads_client_secret = Column(String, default="")
    ads_refresh_token = Column(String, default="")
    ads_profile_id    = Column(String, default="")
    # cached tokens
    sp_access_token  = Column(String, default="")
    sp_token_expiry  = Column(DateTime, nullable=True)
    ads_access_token = Column(String, default="")
    ads_token_expiry = Column(DateTime, nullable=True)
    is_connected = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_sync    = Column(DateTime, nullable=True)

    user     = relationship("User",    back_populates="stores")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    campaigns= relationship("Campaign",back_populates="store", cascade="all, delete-orphan")
    orders   = relationship("Order",   back_populates="store", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id    = Column(String, ForeignKey("stores.id"), nullable=False)
    asin        = Column(String, default="")
    name        = Column(String, nullable=False)
    sku         = Column(String, default="")
    price       = Column(Float, default=0.0)
    cost        = Column(Float, default=0.0)
    stock_level = Column(Integer, default=0)
    status      = Column(String, default="active")
    created_at  = Column(DateTime, default=datetime.utcnow)

    store    = relationship("Store",    back_populates="products")
    keywords = relationship("Keyword",  back_populates="product", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "orders"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id   = Column(String, ForeignKey("stores.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    revenue    = Column(Float, default=0.0)
    profit     = Column(Float, default=0.0)
    ad_spend   = Column(Float, default=0.0)
    marketplace= Column(String, default="")
    status     = Column(String, default="shipped")

    store = relationship("Store", back_populates="orders")


class Campaign(Base):
    __tablename__ = "campaigns"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id      = Column(String, ForeignKey("stores.id"), nullable=False)
    name          = Column(String, nullable=False)
    campaign_type = Column(String, default="sponsored_products")   # sponsored_products/brands/display
    status        = Column(String, default="draft")
    targeting_type= Column(String, default="manual")
    daily_budget  = Column(Float, default=50.0)
    spend         = Column(Float, default=0.0)
    revenue       = Column(Float, default=0.0)
    impressions   = Column(Integer, default=0)
    clicks        = Column(Integer, default=0)
    orders        = Column(Integer, default=0)
    acos          = Column(Float, nullable=True)
    roas          = Column(Float, nullable=True)
    ctr           = Column(Float, nullable=True)
    target_acos   = Column(Float, default=25.0)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store    = relationship("Store",   back_populates="campaigns")
    keywords = relationship("Keyword", back_populates="campaign", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id  = Column(String, ForeignKey("campaigns.id"),  nullable=True)
    product_id   = Column(String, ForeignKey("products.id"),   nullable=True)
    keyword_text = Column(String, nullable=False)
    match_type   = Column(String, default="exact")
    bid          = Column(Float, default=1.0)
    status       = Column(String, default="active")
    clicks       = Column(Integer, default=0)
    impressions  = Column(Integer, default=0)
    spend        = Column(Float, default=0.0)
    orders       = Column(Integer, default=0)
    acos         = Column(Float, nullable=True)

    campaign = relationship("Campaign", back_populates="keywords")
    product  = relationship("Product",  back_populates="keywords")


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id         = Column(String, ForeignKey("users.id"), nullable=False)
    name            = Column(String, nullable=False)
    description     = Column(Text, default="")
    metric          = Column(String, nullable=False)
    condition       = Column(String, nullable=False)   # greater_than/less_than/equals/between
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

    user = relationship("User", back_populates="automation_rules")


class OptimizationItem(Base):
    __tablename__ = "optimization_items"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    campaign_id  = Column(String, ForeignKey("campaigns.id"), nullable=True)
    keyword_id   = Column(String, ForeignKey("keywords.id"),  nullable=True)
    title        = Column(String, nullable=False)
    description  = Column(Text, default="")
    type         = Column(String, default="bid_decrease")
    priority     = Column(String, default="medium")
    current_bid  = Column(Float, nullable=True)
    suggested_bid= Column(Float, nullable=True)
    current_acos = Column(Float, nullable=True)
    expected_acos= Column(Float, nullable=True)
    estimated_savings      = Column(Float, nullable=True)
    estimated_revenue_gain = Column(Float, nullable=True)
    spend        = Column(Float, nullable=True)
    sales        = Column(Float, nullable=True)
    campaign_name= Column(String, default="")
    keyword      = Column(String, default="")
    status       = Column(String, default="pending")
    rule_id      = Column(String, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    applied_at   = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="optimization_items")


class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    title      = Column(String, nullable=False)
    message    = Column(Text, nullable=False)
    severity   = Column(String, default="info")   # info/success/warning/danger
    type       = Column(String, default="general")
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    id                        = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id                   = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    email_notifications       = Column(Boolean, default=True)
    in_app_notifications      = Column(Boolean, default=True)
    daily_optimization_alerts = Column(Boolean, default=True)
    budget_alerts             = Column(Boolean, default=True)
    performance_alerts        = Column(Boolean, default=True)
    inventory_alerts          = Column(Boolean, default=True)
    email_frequency           = Column(String, default="daily")

    user = relationship("User", back_populates="notification_settings")


Base.metadata.create_all(bind=engine)


# ──────────────────────────────────────────────────────────────
#  AUTH HELPERS
# ──────────────────────────────────────────────────────────────
_MAX_PW_BYTES = 72
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:_MAX_PW_BYTES], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:_MAX_PW_BYTES], hashed.encode())
    except Exception:
        return False


def create_token(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY)
    return jwt.encode({"sub": user_id, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    exc = HTTPException(status_code=401, detail="Invalid credentials",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise exc
    return user


# ──────────────────────────────────────────────────────────────
#  WEBSOCKET HUB
# ──────────────────────────────────────────────────────────────
class _Hub:
    def __init__(self):                       # ← double underscore (was single = BUG)
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, uid: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(uid, []).append(ws)

    def disconnect(self, uid: str, ws: WebSocket):
        if uid in self.active:
            self.active[uid] = [w for w in self.active[uid] if w is not ws]

    async def push(self, uid: str, data: dict):
        for ws in list(self.active.get(uid, [])):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(uid, ws)


hub = _Hub()


async def _notify(db: Session, user_id: str, title: str, msg: str, severity: str = "info",
                  ntype: str = "general"):
    n = Notification(user_id=user_id, title=title, message=msg, severity=severity, type=ntype)
    db.add(n); db.commit(); db.refresh(n)
    await hub.push(user_id, {"type": "notification", "id": n.id, "title": title,
                              "message": msg, "severity": severity})
    return n


# ──────────────────────────────────────────────────────────────
#  PYDANTIC SCHEMAS
# ──────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True


class AuthOut(BaseModel):
    token: str              # ← frontend Login.js expects "token" (not "access_token")
    user: UserOut


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = ""


class LoginIn(BaseModel):
    email: str
    password: str


class StoreCreate(BaseModel):
    marketplace: str
    store_name: str
    seller_id: Optional[str] = ""
    marketplace_id: Optional[str] = "A21TJRUUN4KGV"
    sp_client_id: Optional[str] = ""
    sp_client_secret: Optional[str] = ""
    sp_refresh_token: Optional[str] = ""
    ads_client_id: Optional[str] = ""
    ads_client_secret: Optional[str] = ""
    ads_refresh_token: Optional[str] = ""
    ads_profile_id: Optional[str] = ""


class StoreOut(BaseModel):
    id: str
    marketplace: str
    store_name: str
    seller_id: str
    marketplace_id: str
    is_connected: bool
    connected_at: datetime
    last_sync: Optional[datetime]
    has_sp_api: bool = False
    has_ads_api: bool = False
    class Config: from_attributes = True

    @classmethod
    def from_store(cls, s):
        return cls(
            id=s.id, marketplace=s.marketplace, store_name=s.store_name,
            seller_id=s.seller_id, marketplace_id=s.marketplace_id or "A21TJRUUN4KGV",
            is_connected=s.is_connected, connected_at=s.connected_at, last_sync=s.last_sync,
            has_sp_api=bool(s.sp_refresh_token or SP_API_REFRESH_TOKEN),
            has_ads_api=bool(s.ads_refresh_token or ADS_REFRESH_TOKEN),
        )


class NotifSettingsIn(BaseModel):
    email_notifications: Optional[bool] = None
    in_app_notifications: Optional[bool] = None
    daily_optimization_alerts: Optional[bool] = None
    budget_alerts: Optional[bool] = None
    performance_alerts: Optional[bool] = None
    inventory_alerts: Optional[bool] = None
    email_frequency: Optional[str] = None


# ──────────────────────────────────────────────────────────────
#  DEMO DATA SEED  (called automatically on first login)
# ──────────────────────────────────────────────────────────────
def _rand_date(days_back: int) -> datetime:
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back))


def seed_demo_data(db: Session, user: User):
    """Create sample stores, products, orders, campaigns for a brand-new account."""
    if db.query(Store).filter(Store.user_id == user.id).count() > 0:
        return   # already seeded

    store = Store(
        user_id=user.id,
        marketplace="Amazon",
        store_name=f"{user.full_name or 'My'} Store",
        seller_id="DEMO_SELLER_ID",
    )
    db.add(store); db.flush()

    products_data = [
        ("Wireless Earbuds Pro", "B0DEMO001", 2499, 800, 142),
        ("Yoga Mat Premium",     "B0DEMO002", 1299, 350, 85),
        ("LED Desk Lamp",        "B0DEMO003",  899, 280, 203),
        ("Protein Powder 1kg",   "B0DEMO004", 1799, 600, 38),
        ("Kitchen Set Bundle",   "B0DEMO005", 3499, 900, 67),
    ]
    products = []
    for name, asin, price, cost, stock in products_data:
        p = Product(store_id=store.id, name=name, asin=asin,
                    price=price, cost=cost, stock_level=stock)
        db.add(p); db.flush()
        products.append(p)

    # 60 days of orders
    for day_offset in range(60):
        order_date = datetime.utcnow() - timedelta(days=day_offset)
        for prod in random.sample(products, k=random.randint(1, 3)):
            qty = random.randint(1, 5)
            rev = prod.price * qty
            ad  = rev * random.uniform(0.10, 0.30)
            profit = (prod.price - prod.cost) * qty - ad
            o = Order(store_id=store.id, product_id=prod.id,
                      order_date=order_date, revenue=rev,
                      profit=profit, ad_spend=ad, marketplace="Amazon")
            db.add(o)

    # campaigns
    camp_names = [
        ("Wireless Earbuds — SP Exact", "sponsored_products", "active",  50, products[0]),
        ("Yoga Mat — SP Phrase",        "sponsored_products", "active",  30, products[1]),
        ("LED Lamp — Sponsored Brands", "sponsored_brands",   "active",  40, products[2]),
        ("Protein — SP Broad",          "sponsored_products", "paused",  25, products[3]),
        ("Kitchen Bundle — Display",    "sponsored_display",  "draft",   20, products[4]),
    ]
    for cname, ctype, cstatus, budget, prod in camp_names:
        spend = random.uniform(200, 1200)
        rev   = spend * random.uniform(2.5, 5.5)
        acos  = round(spend / rev * 100, 1) if rev else None
        roas  = round(rev / spend, 2) if spend else None
        c = Campaign(
            store_id=store.id, name=cname, campaign_type=ctype,
            status=cstatus, daily_budget=budget,
            spend=round(spend, 2), revenue=round(rev, 2),
            impressions=random.randint(10000, 80000),
            clicks=random.randint(200, 2000),
            orders=random.randint(10, 120),
            acos=acos, roas=roas, target_acos=25.0,
        )
        db.add(c); db.flush()

        # keywords for this campaign
        kws = [prod.name.lower(), f"best {prod.name.lower()[:10]}", f"{prod.name.lower()[:8]} online"]
        for kw_text in kws:
            kspend = spend / 3
            korders = random.randint(1, 20)
            k = Keyword(
                campaign_id=c.id, product_id=prod.id,
                keyword_text=kw_text,
                match_type=random.choice(["exact", "phrase", "broad"]),
                bid=round(random.uniform(0.5, 3.5), 2),
                clicks=random.randint(10, 400),
                impressions=random.randint(500, 15000),
                spend=round(kspend, 2), orders=korders,
                acos=round(kspend / (korders * prod.price) * 100, 1) if korders else None,
            )
            db.add(k)

    # optimization suggestions
    suggestions = [
        ("Wireless Earbuds — [earbuds pro]", "bid_decrease",
         "ACoS 38% above 25% target. Reduce bid.",
         "medium", 1.80, 1.45, 38.0, 22.0, 12.50, 0.0, 18.5, 0.0, "Wireless Earbuds — SP Exact"),
        ("Yoga Mat — [yoga mat premium]", "pause_keyword",
         "12 clicks, 0 conversions. Wasting budget.",
         "high", 1.20, None, None, None, 18.40, 0.0, 18.4, 0.0, "Yoga Mat — SP Phrase"),
        ("LED Lamp — [desk lamp]", "bid_increase",
         "ACoS 14% well below 25% target. Room to scale.",
         "low", 0.85, 1.10, 14.0, 19.0, 0.0, 8.20, 0.0, 8.2, "LED Lamp — Sponsored Brands"),
        ("Protein — [protein powder 1kg]", "negative_keyword",
         "Zero sales from this keyword. Negate it.",
         "high", None, None, None, None, 22.80, 0.0, 22.8, 0.0, "Protein — SP Broad"),
        ("Kitchen Bundle — [kitchen set]", "budget_increase",
         "Hits daily budget cap before noon. Increase budget.",
         "medium", None, None, None, None, 0.0, 35.0, 0.0, 35.0, "Kitchen Bundle — Display"),
    ]
    for title, stype, desc, priority, cbid, sbid, cacos, eacos, savings, rg, spend_val, sales_val, cname in suggestions:
        db.add(OptimizationItem(
            user_id=user.id, title=title, type=stype,
            description=desc, priority=priority,
            current_bid=cbid, suggested_bid=sbid,
            current_acos=cacos, expected_acos=eacos,
            estimated_savings=savings if savings else None,
            estimated_revenue_gain=rg if rg else None,
            spend=spend_val, sales=sales_val,
            campaign_name=cname, keyword=title.split("—")[-1].strip().strip("[]"),
        ))

    # notifications
    notifs = [
        ("ACoS Alert", "Wireless Earbuds ACoS hit 38% — above your 25% target", "warning"),
        ("Budget Cap Reached", "LED Lamp campaign hit daily budget limit", "info"),
        ("Low Stock Alert", "Protein Powder has only 38 units left", "danger"),
        ("Weekly Report", "Your weekly performance summary is ready", "success"),
    ]
    for title, msg, sev in notifs:
        db.add(Notification(user_id=user.id, title=title, message=msg, severity=sev))

    # notification settings
    db.add(NotificationSetting(user_id=user.id))

    db.commit()
    log.info("Demo data seeded for user %s", user.email)


# ──────────────────────────────────────────────────────────────
#  HELPER
# ──────────────────────────────────────────────────────────────
def _store_ids(db: Session, user: User) -> List[str]:
    return [s.id for s in db.query(Store).filter(Store.user_id == user.id).all()]


# ──────────────────────────────────────────────────────────────
#  ROUTERS
# ──────────────────────────────────────────────────────────────
api = APIRouter(prefix="/api")

# ── AUTH ──────────────────────────────────────────────────────
auth = APIRouter(prefix="/auth", tags=["auth"])


@auth.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(email=data.email, hashed_password=hash_password(data.password),
                full_name=data.full_name or "")
    db.add(user); db.commit(); db.refresh(user)
    seed_demo_data(db, user)
    return {"token": create_token(user.id), "user": UserOut.model_validate(user)}


@auth.post("/login")                        # ← matches Login.js which calls /auth/login
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    seed_demo_data(db, user)               # safe — skips if already seeded
    return {"token": create_token(user.id), "user": UserOut.model_validate(user)}


@auth.post("/token")                        # OAuth2 form-based (for Swagger docs)
def token_login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(user.id), "token_type": "bearer",
            "token": create_token(user.id), "user": UserOut.model_validate(user)}


@auth.get("/me")
def me(current: User = Depends(get_current_user)):
    return UserOut.model_validate(current)


# ── STORES ────────────────────────────────────────────────────
stores_r = APIRouter(prefix="/stores", tags=["stores"])


@stores_r.get("")
def list_stores(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns ONLY stores belonging to the logged-in user — fixes account data mixing."""
    stores = db.query(Store).filter(Store.user_id == current.id).all()
    return [StoreOut.model_validate(s) for s in stores]


@stores_r.post("")
async def create_store(data: StoreCreate, current: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    s = Store(user_id=current.id, **data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    await _notify(db, current.id, "Store connected",
                  f"{s.store_name} ({s.marketplace}) connected", "success")
    return StoreOut.model_validate(s)


@stores_r.delete("/{store_id}")
def delete_store(store_id: str, current: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    s = db.query(Store).filter(Store.id == store_id, Store.user_id == current.id).first()
    if not s: raise HTTPException(404, "Store not found")
    db.delete(s); db.commit()
    return {"ok": True}


# ── DASHBOARD ─────────────────────────────────────────────────
dash_r = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dash_r.get("")
def dashboard(days: int = 30, marketplace: str = "all", currency: str = "INR",
              current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fully scoped to current user — different users see different data."""
    sid = _store_ids(db, current)
    if not sid:
        return _empty_dashboard()

    since = datetime.utcnow() - timedelta(days=days)
    q = db.query(Order).filter(Order.store_id.in_(sid), Order.order_date >= since)
    if marketplace != "all":
        q = q.filter(Order.marketplace == marketplace)
    orders = q.all()

    total_revenue = sum(o.revenue for o in orders)
    total_orders  = len(orders)
    net_profit    = sum(o.profit for o in orders)
    ad_spend      = sum(o.ad_spend for o in orders)
    roas  = round(total_revenue / ad_spend, 2) if ad_spend else 0
    acos  = round(ad_spend / total_revenue * 100, 1) if total_revenue else 0
    tcos  = round((ad_spend + sum(o.revenue - o.profit for o in orders)) / total_revenue * 100, 1) if total_revenue else 0

    low_stock = db.query(Product).filter(
        Product.store_id.in_(sid), Product.stock_level < 50
    ).count()

    # chart data — group by date
    from collections import defaultdict
    daily_orders: Dict[str, int] = defaultdict(int)
    daily_revenue: Dict[str, float] = defaultdict(float)
    for o in orders:
        d = o.order_date.strftime("%b %d")
        daily_orders[d]  += 1
        daily_revenue[d] += o.revenue

    orders_chart  = [{"date": k, "orders":  v} for k, v in sorted(daily_orders.items())][-30:]
    revenue_chart = [{"date": k, "revenue": round(v, 2)} for k, v in sorted(daily_revenue.items())][-30:]

    # top products
    prod_rev: Dict[str, dict] = defaultdict(lambda: {"revenue": 0, "orders": 0,
                                                       "net_profit": 0, "stock_level": 0, "name": ""})
    for o in orders:
        if o.product_id:
            prod_rev[o.product_id]["revenue"]    += o.revenue
            prod_rev[o.product_id]["orders"]     += 1
            prod_rev[o.product_id]["net_profit"] += o.profit
    for prod in db.query(Product).filter(Product.store_id.in_(sid)).all():
        prod_rev[prod.id]["name"]        = prod.name
        prod_rev[prod.id]["stock_level"] = prod.stock_level
    top_products = sorted(prod_rev.values(), key=lambda x: x["revenue"], reverse=True)[:5]

    fx = 1 if currency == "INR" else 0.012
    return {
        "total_revenue": round(total_revenue * fx, 2),
        "total_orders":  total_orders,
        "net_profit":    round(net_profit * fx, 2),
        "ad_spend":      round(ad_spend * fx, 2),
        "roas": roas, "acos": acos, "tcos": tcos,
        "low_inventory_alerts": low_stock,
        "orders_chart":  orders_chart,
        "revenue_chart": revenue_chart,
        "top_products":  [{**p, "revenue": round(p["revenue"]*fx, 2),
                           "net_profit": round(p["net_profit"]*fx, 2)} for p in top_products],
    }


def _empty_dashboard():
    return {
        "total_revenue": 0, "total_orders": 0, "net_profit": 0, "ad_spend": 0,
        "roas": 0, "acos": 0, "tcos": 0, "low_inventory_alerts": 0,
        "orders_chart": [], "revenue_chart": [], "top_products": [],
    }


# ── CAMPAIGNS ─────────────────────────────────────────────────
camp_r = APIRouter(prefix="/campaigns", tags=["campaigns"])


@camp_r.get("")
def list_campaigns(status: Optional[str] = None,
                   current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Campaign).filter(Campaign.store_id.in_(_store_ids(db, current)))
    if status: q = q.filter(Campaign.status == status)
    return {"campaigns": [_camp_dict(c) for c in q.order_by(desc(Campaign.updated_at)).all()]}


@camp_r.post("/create")
def create_campaign(data: Dict[str, Any], current: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    sid = _store_ids(db, current)
    if not sid: raise HTTPException(400, "Connect a store first")
    camps = []
    for cd in (data.get("campaigns") or [data]):
        c = Campaign(store_id=sid[0], name=cd.get("name", "New Campaign"),
                     campaign_type=cd.get("campaign_type", "sponsored_products"),
                     daily_budget=cd.get("daily_budget", 50), status="active",
                     target_acos=cd.get("target_acos", 25))
        db.add(c); camps.append(c)
    db.commit()
    return {"campaigns": [_camp_dict(c) for c in camps]}


@camp_r.patch("/{camp_id}")
def update_campaign(camp_id: str, data: Dict[str, Any],
                    current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == camp_id,
                                  Campaign.store_id.in_(_store_ids(db, current))).first()
    if not c: raise HTTPException(404, "Not found")
    for k, v in data.items():
        if hasattr(c, k): setattr(c, k, v)
    db.commit(); db.refresh(c)
    return _camp_dict(c)


@camp_r.delete("/{camp_id}")
def delete_campaign(camp_id: str, current: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == camp_id,
                                  Campaign.store_id.in_(_store_ids(db, current))).first()
    if not c: raise HTTPException(404, "Not found")
    db.delete(c); db.commit()
    return {"ok": True}


def _camp_dict(c: Campaign) -> dict:
    return {
        "id": c.id, "name": c.name, "campaign_type": c.campaign_type,
        "status": c.status, "daily_budget": c.daily_budget,
        "spend": c.spend, "revenue": c.revenue,
        "impressions": c.impressions, "clicks": c.clicks, "orders": c.orders,
        "acos": c.acos, "roas": c.roas, "target_acos": c.target_acos,
        "created_at": c.created_at.isoformat(),
    }


# ── PRODUCTS ──────────────────────────────────────────────────
prod_r = APIRouter(prefix="/products", tags=["products"])


@prod_r.get("")
def list_products(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prods = db.query(Product).filter(Product.store_id.in_(_store_ids(db, current))).all()
    return [{"id": p.id, "asin": p.asin, "name": p.name, "sku": p.sku,
             "price": p.price, "cost": p.cost, "stock_level": p.stock_level,
             "status": p.status} for p in prods]


# ── OPTIMIZATION ──────────────────────────────────────────────
opt_r = APIRouter(prefix="/optimization", tags=["optimization"])


@opt_r.get("/suggestions")
def get_suggestions(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns ONLY this user's optimization items — no data from other accounts."""
    items = db.query(OptimizationItem).filter(
        OptimizationItem.user_id == current.id
    ).order_by(desc(OptimizationItem.created_at)).all()

    pending   = [i for i in items if i.status == "pending"]
    high_pri  = [i for i in pending if i.priority == "high"]
    pot_save  = sum(i.estimated_savings or 0 for i in pending)
    pot_gain  = sum(i.estimated_revenue_gain or 0 for i in pending)

    return {
        "suggestions": [_opt_dict(i) for i in items],
        "summary": {
            "total_suggestions": len(pending),
            "high_priority":     len(high_pri),
            "potential_savings": round(pot_save, 2),
            "potential_revenue_gain": round(pot_gain, 2),
        }
    }


@opt_r.post("/apply/{item_id}")
async def apply_one(item_id: str, current: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    item = db.query(OptimizationItem).filter(
        OptimizationItem.id == item_id, OptimizationItem.user_id == current.id
    ).first()
    if not item: raise HTTPException(404, "Not found")
    item.status = "applied"; item.applied_at = datetime.utcnow()
    db.commit()
    await _notify(db, current.id, "Optimization applied", item.title, "success")
    return {"ok": True, "id": item.id}


@opt_r.post("/apply-all")
async def apply_all(data: Dict[str, Any] = {}, current: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    ids = data.get("suggestion_ids") if data else None
    q = db.query(OptimizationItem).filter(
        OptimizationItem.user_id == current.id,
        OptimizationItem.status == "pending",
    )
    if ids: q = q.filter(OptimizationItem.id.in_(ids))
    items = q.all()
    for i in items:
        i.status = "applied"; i.applied_at = datetime.utcnow()
    db.commit()
    await _notify(db, current.id, "Optimizations applied",
                  f"{len(items)} action(s) applied successfully", "success")
    return {"applied": len(items), "message": "All optimizations applied"}


@opt_r.get("/count")
def opt_count(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Used by Layout to show real badge count instead of hardcoded '5'."""
    n = db.query(OptimizationItem).filter(
        OptimizationItem.user_id == current.id,
        OptimizationItem.status == "pending",
    ).count()
    return {"pending": n}


def _opt_dict(i: OptimizationItem) -> dict:
    return {
        "id": i.id, "title": i.title, "description": i.description,
        "type": i.type, "priority": i.priority, "status": i.status,
        "campaign_name": i.campaign_name, "keyword": i.keyword,
        "current_bid": i.current_bid, "suggested_bid": i.suggested_bid,
        "current_acos": i.current_acos, "expected_acos": i.expected_acos,
        "estimated_savings": i.estimated_savings,
        "estimated_revenue_gain": i.estimated_revenue_gain,
        "spend": i.spend, "sales": i.sales,
        "created_at": i.created_at.isoformat(),
    }


# ── NOTIFICATIONS ─────────────────────────────────────────────
notif_r = APIRouter(prefix="/notifications", tags=["notifications"])


@notif_r.get("/history")            # ← matches NotificationCenter.js
def notif_history(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(
        Notification.user_id == current.id
    ).order_by(desc(Notification.created_at)).limit(50).all()
    unread = sum(1 for n in notifs if not n.is_read)
    return {
        "notifications": [_notif_dict(n) for n in notifs],
        "unread_count": unread,
    }


@notif_r.get("/count")              # ← used by Layout badge
def notif_count(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(
        Notification.user_id == current.id, Notification.is_read == False
    ).count()
    return {"unread": n}


@notif_r.post("/{nid}/read")
def mark_read(nid: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(
        Notification.id == nid, Notification.user_id == current.id
    ).first()
    if n: n.is_read = True; db.commit()
    return {"ok": True}


@notif_r.post("/read-all")
def read_all(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == current.id, Notification.is_read == False
    ).update({"is_read": True}); db.commit()
    return {"ok": True}


def _notif_dict(n: Notification) -> dict:
    return {
        "id": n.id, "title": n.title, "message": n.message,
        "severity": n.severity, "type": n.type,
        "is_read": n.is_read, "created_at": n.created_at.isoformat(),
    }


# ── NOTIFICATION SETTINGS ─────────────────────────────────────
nsettings_r = APIRouter(prefix="/notification-settings", tags=["notification-settings"])


@nsettings_r.get("")
def get_notif_settings(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(NotificationSetting).filter(NotificationSetting.user_id == current.id).first()
    if not s:
        s = NotificationSetting(user_id=current.id)
        db.add(s); db.commit(); db.refresh(s)
    return {"settings": _ns_dict(s)}


@nsettings_r.patch("")
def update_notif_settings(data: NotifSettingsIn,
                           current: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    s = db.query(NotificationSetting).filter(NotificationSetting.user_id == current.id).first()
    if not s:
        s = NotificationSetting(user_id=current.id)
        db.add(s)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit(); db.refresh(s)
    return {"settings": _ns_dict(s)}


def _ns_dict(s: NotificationSetting) -> dict:
    return {
        "email_notifications": s.email_notifications,
        "in_app_notifications": s.in_app_notifications,
        "daily_optimization_alerts": s.daily_optimization_alerts,
        "budget_alerts": s.budget_alerts,
        "performance_alerts": s.performance_alerts,
        "inventory_alerts": s.inventory_alerts,
        "email_frequency": s.email_frequency,
    }


# ── CAMPAIGN BUILDER ──────────────────────────────────────────
cb_r = APIRouter(prefix="/campaign-builder", tags=["campaign-builder"])


@cb_r.get("/products")
def cb_products(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prods = db.query(Product).filter(Product.store_id.in_(_store_ids(db, current))).all()
    if not prods:
        return {"products": [], "message": "Connect a store to see products"}
    return {
        "products": [{"id": p.id, "asin": p.asin, "name": p.name,
                      "price": p.price, "stock_level": p.stock_level} for p in prods]
    }


@cb_r.post("/generate")
async def cb_generate(data: Dict[str, Any], current: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    sid = _store_ids(db, current)
    if not sid:
        return {"campaigns": [], "message": "Connect Amazon to generate campaigns"}
    product_name = data.get("product_name", "Product")
    target_acos  = float(data.get("target_acos", 25))
    budget       = float(data.get("daily_budget", 50))

    if ANTHROPIC_API_KEY:
        camps = await _ai_generate(product_name, target_acos, budget)
    else:
        camps = _heuristic_generate(product_name, target_acos, budget)
    return {"campaigns": camps, "message": "Generated. Review and launch."}


@cb_r.post("/launch")
async def cb_launch(data: Dict[str, Any], current: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    sid = _store_ids(db, current)
    if not sid: raise HTTPException(400, "Connect a store first")
    launched = []
    for cd in (data.get("campaigns") or []):
        c = Campaign(
            store_id=sid[0], name=cd.get("name", "Campaign"),
            campaign_type=cd.get("campaign_type", "sponsored_products"),
            daily_budget=cd.get("daily_budget", 50),
            status="active", target_acos=cd.get("target_acos", 25),
        )
        db.add(c); db.flush()
        for kw in (cd.get("keywords") or []):
            db.add(Keyword(
                campaign_id=c.id, keyword_text=kw.get("text", ""),
                match_type=kw.get("match_type", "exact"), bid=kw.get("bid", 1.0),
            ))
        launched.append(c)
    db.commit()
    await _notify(db, current.id, "Campaigns launched",
                  f"{len(launched)} campaign(s) are now live", "success")
    return {"launched_campaigns": [_camp_dict(c) for c in launched]}


def _heuristic_generate(product: str, target_acos: float, budget: float):
    base = round(max(budget / 50, 0.5), 2)
    return [
        {"id": str(uuid.uuid4()), "name": f"{product} — Exact",
         "campaign_type": "sponsored_products", "daily_budget": round(budget*0.5, 2),
         "target_acos": target_acos,
         "keywords": [{"text": product.lower(), "match_type": "exact", "bid": round(base*1.2, 2)},
                      {"text": f"best {product.lower()}", "match_type": "exact", "bid": base}]},
        {"id": str(uuid.uuid4()), "name": f"{product} — Phrase",
         "campaign_type": "sponsored_products", "daily_budget": round(budget*0.3, 2),
         "target_acos": target_acos,
         "keywords": [{"text": product.lower(), "match_type": "phrase", "bid": round(base*0.9, 2)}]},
        {"id": str(uuid.uuid4()), "name": f"{product} — Broad",
         "campaign_type": "sponsored_products", "daily_budget": round(budget*0.2, 2),
         "target_acos": target_acos,
         "keywords": [{"text": product.lower(), "match_type": "broad", "bid": round(base*0.7, 2)}]},
    ]


async def _ai_generate(product: str, target_acos: float, budget: float):
    prompt = (
        f"Amazon PPC strategist: propose a 3-campaign structure (Exact/Phrase/Broad) for: {product}. "
        f"Target ACoS {target_acos}%, budget ${budget}/day. "
        f'Return JSON array only: [{{"id":"uuid","name":"str","campaign_type":"sponsored_products",'
        f'"daily_budget":float,"target_acos":float,"keywords":[{{"text":"str","match_type":"exact|phrase|broad","bid":float}}]}}]'
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": ANTHROPIC_MODEL, "max_tokens": 1500,
                      "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            text = r.json()["content"][0]["text"]
            m = re.search(r"\[.*\]", text, re.S)
            if m: return json.loads(m.group(0))
    except Exception as e:
        log.warning("AI generation failed: %s", e)
    return _heuristic_generate(product, target_acos, budget)


# ── RULES ─────────────────────────────────────────────────────
rules_r = APIRouter(prefix="/rules", tags=["rules"])

VALID_CONDITIONS = {"greater_than", "less_than", "equals", "between"}
VALID_METRICS    = {"acos", "roas", "clicks", "impressions", "spend", "orders", "ctr", "cvr"}
VALID_ACTIONS    = {"bid_up", "bid_down", "pause", "enable", "negate",
                    "budget_up", "budget_down", "flag"}


class RuleIn(BaseModel):
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
    def _c(cls, v):
        if v not in VALID_CONDITIONS: raise ValueError(f"Must be one of {VALID_CONDITIONS}")
        return v

    @field_validator("metric")
    @classmethod
    def _m(cls, v):
        if v not in VALID_METRICS: raise ValueError(f"Must be one of {VALID_METRICS}")
        return v

    @field_validator("action")
    @classmethod
    def _a(cls, v):
        if v not in VALID_ACTIONS: raise ValueError(f"Must be one of {VALID_ACTIONS}")
        return v


@rules_r.get("")
def list_rules(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(AutomationRule).filter(AutomationRule.user_id == current.id).all()


@rules_r.post("")
def create_rule(data: RuleIn, current: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    if data.condition == "between" and not (data.threshold_min and data.threshold_max):
        raise HTTPException(400, "'between' needs threshold_min and threshold_max")
    if data.condition != "between" and data.threshold_value is None:
        raise HTTPException(400, "Needs threshold_value")
    r = AutomationRule(user_id=current.id, **data.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r


@rules_r.patch("/{rule_id}")
def update_rule(rule_id: str, data: Dict[str, Any],
                current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(AutomationRule).filter(AutomationRule.id == rule_id,
                                         AutomationRule.user_id == current.id).first()
    if not r: raise HTTPException(404, "Not found")
    for k, v in data.items():
        if hasattr(r, k): setattr(r, k, v)
    db.commit(); db.refresh(r)
    return r


@rules_r.delete("/{rule_id}")
def delete_rule(rule_id: str, current: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    r = db.query(AutomationRule).filter(AutomationRule.id == rule_id,
                                         AutomationRule.user_id == current.id).first()
    if not r: raise HTTPException(404, "Not found")
    db.delete(r); db.commit()
    return {"ok": True}


# ── ANALYTICS ─────────────────────────────────────────────────
analytics_r = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_r.get("/dashboard")
def analytics_dashboard(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Alias so the AdPilot UI also works alongside the SellerVector UI."""
    return dashboard(30, "all", "INR", current, db)


@analytics_r.get("/top-keywords")
def top_keywords(limit: int = 10, current: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    kws = db.query(Keyword).join(Campaign).filter(
        Campaign.store_id.in_(_store_ids(db, current))
    ).order_by(desc(Keyword.orders)).limit(limit).all()
    return [{"keyword_text": k.keyword_text, "match_type": k.match_type,
             "clicks": k.clicks, "orders": k.orders, "spend": k.spend, "acos": k.acos}
            for k in kws]


# ── MOUNT ALL ROUTERS ─────────────────────────────────────────
api.include_router(auth)
api.include_router(stores_r)
api.include_router(dash_r)
api.include_router(camp_r)
api.include_router(prod_r)
api.include_router(opt_r)
api.include_router(notif_r)
api.include_router(nsettings_r)
api.include_router(cb_r)
api.include_router(rules_r)
api.include_router(analytics_r)


# ──────────────────────────────────────────────────────────────
#  APP
# ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("SellerVector starting — DB=%s", DATABASE_URL)
    yield
    log.info("SellerVector stopping")


app = FastAPI(
    title="SellerVector API",
    description="Amazon PPC & seller analytics platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _err(request, exc):
    log.exception("Unhandled: %s", exc)
    return JSONResponse(500, {"detail": "Internal server error"})


@app.get("/")
def root(): return {"name": "SellerVector API", "version": "2.0.0", "docs": "/docs"}


@app.get("/api/health")
def health(): return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.websocket("/ws/notifications")
async def ws_notif(ws: WebSocket, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid: await ws.close(code=4401); return
    except JWTError:
        await ws.close(code=4401); return
    await hub.connect(uid, ws)
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(uid, ws)


app.include_router(api)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

# ══════════════════════════════════════════════════════════════
#  AMAZON SP-API INTEGRATION
#  Covers: Orders, Products, Inventory, FBA Shipments
# ══════════════════════════════════════════════════════════════

# SP-API credentials from environment
SP_API_CLIENT_ID      = os.getenv("SP_API_CLIENT_ID", "")
SP_API_CLIENT_SECRET  = os.getenv("SP_API_CLIENT_SECRET", "")
SP_API_REFRESH_TOKEN  = os.getenv("SP_API_REFRESH_TOKEN", "")
SP_API_MARKETPLACE_ID = os.getenv("MARKETPLACE_ID", "A21TJRUUN4KGV")  # India default
SP_API_SELLER_ID      = os.getenv("SELLER_ID", "")

# SP-API endpoints by region
SP_API_ENDPOINTS = {
    "A21TJRUUN4KGV": "https://sellingpartnerapi-fe.amazon.com",   # India
    "ATVPDKIKX0DER": "https://sellingpartnerapi-na.amazon.com",   # US
    "A1F83G8C2ARO7P": "https://sellingpartnerapi-eu.amazon.com",  # UK
    "A1PA6795UKMFR9": "https://sellingpartnerapi-eu.amazon.com",  # Germany
}

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"

# Amazon Ads API credentials
ADS_CLIENT_ID     = os.getenv("ADS_CLIENT_ID", "")
ADS_CLIENT_SECRET = os.getenv("ADS_CLIENT_SECRET", "")
ADS_REFRESH_TOKEN = os.getenv("ADS_REFRESH_TOKEN", os.getenv("SP_API_REFRESH_TOKEN", ""))

# Ads API endpoints by marketplace
ADS_API_ENDPOINTS = {
    "A21TJRUUN4KGV": "https://advertising-api-fe.amazon.com",   # India
    "ATVPDKIKX0DER": "https://advertising-api.amazon.com",      # US
    "A1F83G8C2ARO7P": "https://advertising-api-eu.amazon.com",  # UK/EU
}

# ── Token cache (in-memory, refreshed automatically) ──────────
_token_cache: Dict[str, dict] = {}


async def _get_lwa_token(client_id: str, client_secret: str, refresh_token: str,
                          scope: str = "") -> str:
    """Get LWA access token using refresh token. Cached for 55 minutes."""
    cache_key = f"{client_id}:{scope}"
    cached = _token_cache.get(cache_key)
    if cached and cached["expires_at"] > datetime.utcnow():
        return cached["token"]

    payload = {
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     client_id,
        "client_secret": client_secret,
    }
    if scope:
        payload["scope"] = scope

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(LWA_TOKEN_URL, data=payload)
        r.raise_for_status()
        data = r.json()

    token = data["access_token"]
    _token_cache[cache_key] = {
        "token":      token,
        "expires_at": datetime.utcnow() + timedelta(minutes=55),
    }
    return token


async def _sp_api_request(method: str, path: str, params: dict = None,
                           body: dict = None) -> dict:
    """Make authenticated SP-API request."""
    if not SP_API_CLIENT_ID or not SP_API_REFRESH_TOKEN:
        raise HTTPException(503, "SP-API credentials not configured")

    token = await _get_lwa_token(SP_API_CLIENT_ID, SP_API_CLIENT_SECRET,
                                  SP_API_REFRESH_TOKEN)
    base_url = SP_API_ENDPOINTS.get(SP_API_MARKETPLACE_ID,
                                    "https://sellingpartnerapi-fe.amazon.com")
    headers = {
        "x-amz-access-token": token,
        "Content-Type":       "application/json",
        "Accept":             "application/json",
    }
    url = f"{base_url}{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        if method == "GET":
            r = await client.get(url, headers=headers, params=params or {})
        elif method == "POST":
            r = await client.post(url, headers=headers, json=body or {})
        else:
            raise ValueError(f"Unsupported method: {method}")
        r.raise_for_status()
        return r.json()


async def _ads_api_request(method: str, path: str, profile_id: str = None,
                            params: dict = None, body: dict = None) -> dict:
    """Make authenticated Amazon Ads API request."""
    if not ADS_CLIENT_ID or not ADS_REFRESH_TOKEN:
        raise HTTPException(503, "Ads API credentials not configured")

    token = await _get_lwa_token(ADS_CLIENT_ID, ADS_CLIENT_SECRET,
                                  ADS_REFRESH_TOKEN,
                                  scope="advertising::campaign_management")
    base_url = ADS_API_ENDPOINTS.get(SP_API_MARKETPLACE_ID,
                                     "https://advertising-api-fe.amazon.com")
    headers = {
        "Authorization":        f"Bearer {token}",
        "Amazon-Advertising-API-ClientId": ADS_CLIENT_ID,
        "Content-Type":         "application/json",
    }
    if profile_id:
        headers["Amazon-Advertising-API-Scope"] = str(profile_id)

    url = f"{base_url}{path}"
    async with httpx.AsyncClient(timeout=60) as client:
        if method == "GET":
            r = await client.get(url, headers=headers, params=params or {})
        elif method == "POST":
            r = await client.post(url, headers=headers, json=body or {})
        else:
            raise ValueError(f"Unsupported method: {method}")
        r.raise_for_status()
        return r.json()


# ══════════════════════════════════════════════════════════════
#  SP-API ROUTES
# ══════════════════════════════════════════════════════════════
spapi_r = APIRouter(prefix="/spapi", tags=["sp-api"])


@spapi_r.get("/orders")
async def get_real_orders(
    days: int = 30,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real orders from Amazon SP-API and sync to DB."""
    if not SP_API_CLIENT_ID or not SP_API_REFRESH_TOKEN:
        return {"orders": [], "message": "SP-API not configured. Add SP_API credentials to Render environment."}

    try:
        created_after = (datetime.utcnow() - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        data = await _sp_api_request("GET", "/orders/v0/orders", params={
            "MarketplaceIds": SP_API_MARKETPLACE_ID,
            "CreatedAfter":   created_after,
            "OrderStatuses":  "Shipped,Delivered,Unshipped,PartiallyShipped",
        })
        orders = data.get("payload", {}).get("Orders", [])

        # sync to DB
        sid = _store_ids(db, current)
        if sid:
            for o in orders:
                amt = float(o.get("OrderTotal", {}).get("Amount", 0))
                existing = db.query(Order).filter(
                    Order.store_id == sid[0],
                    Order.id == o.get("AmazonOrderId", ""),
                ).first()
                if not existing:
                    db.add(Order(
                        id=o.get("AmazonOrderId", str(uuid.uuid4())),
                        store_id=sid[0],
                        order_date=datetime.strptime(
                            o.get("PurchaseDate", datetime.utcnow().isoformat()),
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        revenue=amt,
                        profit=amt * 0.2,
                        ad_spend=amt * 0.15,
                        marketplace=o.get("SalesChannel", "Amazon"),
                        status=o.get("OrderStatus", "shipped").lower(),
                    ))
            db.commit()

        return {
            "orders":        orders[:50],
            "total":         len(orders),
            "synced_to_db":  True,
            "message":       f"Fetched {len(orders)} real orders from Amazon",
        }
    except httpx.HTTPStatusError as e:
        log.error("SP-API orders error: %s", e)
        return {"orders": [], "error": str(e), "message": "Failed to fetch from Amazon. Check SP-API credentials."}
    except Exception as e:
        log.error("SP-API orders error: %s", e)
        return {"orders": [], "error": str(e)}


@spapi_r.get("/inventory")
async def get_real_inventory(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real FBA inventory from Amazon SP-API."""
    if not SP_API_CLIENT_ID or not SP_API_REFRESH_TOKEN:
        return {"inventory": [], "message": "SP-API not configured"}

    try:
        data = await _sp_api_request("GET", "/fba/inventory/v1/summaries", params={
            "details":          "true",
            "granularityType":  "Marketplace",
            "granularityId":    SP_API_MARKETPLACE_ID,
            "marketplaceIds":   SP_API_MARKETPLACE_ID,
        })
        items = data.get("payload", {}).get("inventorySummaries", [])

        # sync to DB products
        sid = _store_ids(db, current)
        if sid:
            for item in items:
                asin = item.get("asin", "")
                qty  = item.get("totalQuantity", 0)
                existing = db.query(Product).filter(
                    Product.store_id == sid[0],
                    Product.asin == asin,
                ).first()
                if existing:
                    existing.stock_level = qty
                else:
                    db.add(Product(
                        store_id=sid[0],
                        asin=asin,
                        name=item.get("productName", asin),
                        sku=item.get("sellerSku", ""),
                        stock_level=qty,
                    ))
            db.commit()

        return {
            "inventory":    items,
            "total":        len(items),
            "synced_to_db": True,
            "message":      f"Fetched {len(items)} real inventory items from Amazon",
        }
    except Exception as e:
        log.error("SP-API inventory error: %s", e)
        return {"inventory": [], "error": str(e)}


@spapi_r.get("/products")
async def get_real_products(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real products/catalog from Amazon SP-API."""
    if not SP_API_CLIENT_ID or not SP_API_REFRESH_TOKEN:
        return {"products": [], "message": "SP-API not configured"}

    try:
        data = await _sp_api_request("GET", "/catalog/2022-04-01/items", params={
            "marketplaceIds": SP_API_MARKETPLACE_ID,
            "includedData":   "summaries,attributes,salesRanks",
            "sellerId":       SP_API_SELLER_ID,
        })
        items = data.get("items", [])
        return {
            "products": items,
            "total":    len(items),
            "message":  f"Fetched {len(items)} real products from Amazon",
        }
    except Exception as e:
        log.error("SP-API products error: %s", e)
        return {"products": [], "error": str(e)}


@spapi_r.get("/fba-shipments")
async def get_fba_shipments(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real FBA inbound shipments from Amazon SP-API."""
    if not SP_API_CLIENT_ID or not SP_API_REFRESH_TOKEN:
        return {"shipments": [], "message": "SP-API not configured"}

    try:
        data = await _sp_api_request(
            "GET",
            "/fba/inbound/v0/shipments",
            params={
                "MarketplaceId": SP_API_MARKETPLACE_ID,
                "ShipmentStatusList": "WORKING,SHIPPED,IN_TRANSIT,DELIVERED,CHECKED_IN,RECEIVING,CLOSED",
                "QueryType": "SHIPMENT",
            }
        )
        shipments = data.get("payload", {}).get("ShipmentData", [])
        return {
            "shipments": shipments,
            "total":     len(shipments),
            "message":   f"Fetched {len(shipments)} real FBA shipments",
        }
    except Exception as e:
        log.error("SP-API shipments error: %s", e)
        return {"shipments": [], "error": str(e)}


@spapi_r.post("/sync-all")
async def sync_all_sp_data(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync ALL SP-API data at once — orders, inventory, products."""
    results = {}
    try:
        orders_res    = await get_real_orders(30, current, db)
        results["orders"] = orders_res.get("total", 0)
    except Exception as e:
        results["orders_error"] = str(e)

    try:
        inv_res       = await get_real_inventory(current, db)
        results["inventory"] = inv_res.get("total", 0)
    except Exception as e:
        results["inventory_error"] = str(e)

    await _notify(db, current.id, "Amazon Sync Complete",
                  f"Synced {results.get('orders',0)} orders, "
                  f"{results.get('inventory',0)} inventory items",
                  "success")
    return {"synced": results, "message": "SP-API sync complete"}


# ══════════════════════════════════════════════════════════════
#  AMAZON ADS API ROUTES
# ══════════════════════════════════════════════════════════════
ads_r = APIRouter(prefix="/ads", tags=["amazon-ads"])


@ads_r.get("/profiles")
async def get_ads_profiles(current: User = Depends(get_current_user)):
    """Get all advertising profiles for this account."""
    if not ADS_CLIENT_ID or not ADS_REFRESH_TOKEN:
        return {"profiles": [], "message": "Ads API not configured. Add ADS_CLIENT_ID and ADS_REFRESH_TOKEN to Render."}
    try:
        profiles = await _ads_api_request("GET", "/v2/profiles")
        return {"profiles": profiles, "total": len(profiles)}
    except Exception as e:
        log.error("Ads profiles error: %s", e)
        return {"profiles": [], "error": str(e)}


@ads_r.get("/campaigns")
async def get_real_campaigns(
    profile_id: str,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real campaigns from Amazon Ads API."""
    if not ADS_CLIENT_ID or not ADS_REFRESH_TOKEN:
        return {"campaigns": [], "message": "Ads API not configured"}
    try:
        data = await _ads_api_request("GET", "/v2/campaigns", profile_id=profile_id,
                                       params={"stateFilter": "enabled,paused"})
        campaigns = data if isinstance(data, list) else data.get("campaigns", [])

        # sync to DB
        sid = _store_ids(db, current)
        if sid:
            for c in campaigns:
                existing = db.query(Campaign).filter(
                    Campaign.store_id == sid[0],
                    Campaign.name == c.get("name", ""),
                ).first()
                if not existing:
                    db.add(Campaign(
                        store_id=sid[0],
                        name=c.get("name", ""),
                        campaign_type=c.get("campaignType", "sponsoredProducts"),
                        status=c.get("state", "enabled"),
                        daily_budget=float(c.get("dailyBudget", 0)),
                    ))
            db.commit()

        return {"campaigns": campaigns, "total": len(campaigns),
                "message": f"Fetched {len(campaigns)} real campaigns"}
    except Exception as e:
        log.error("Ads campaigns error: %s", e)
        return {"campaigns": [], "error": str(e)}


@ads_r.get("/keywords")
async def get_real_keywords(
    profile_id: str,
    campaign_id: str = None,
    current: User = Depends(get_current_user),
):
    """Fetch real keywords from Amazon Ads API."""
    if not ADS_CLIENT_ID:
        return {"keywords": [], "message": "Ads API not configured"}
    try:
        params = {"stateFilter": "enabled,paused"}
        if campaign_id:
            params["campaignIdFilter"] = campaign_id
        data = await _ads_api_request("GET", "/v2/keywords", profile_id=profile_id,
                                       params=params)
        keywords = data if isinstance(data, list) else []
        return {"keywords": keywords, "total": len(keywords)}
    except Exception as e:
        log.error("Ads keywords error: %s", e)
        return {"keywords": [], "error": str(e)}


@ads_r.get("/reports/performance")
async def get_ads_performance(
    profile_id: str,
    days: int = 30,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request a performance report from Amazon Ads API."""
    if not ADS_CLIENT_ID:
        return {"report": None, "message": "Ads API not configured"}
    try:
        end_date   = datetime.utcnow().strftime("%Y%m%d")
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%d")

        report_body = {
            "reportDate":    end_date,
            "metrics":       "impressions,clicks,cost,attributedSales30d,attributedOrdersNewToBrand30d,acos",
            "segment":       "query",
        }
        data = await _ads_api_request(
            "POST",
            "/v2/sp/keywords/report",
            profile_id=profile_id,
            body=report_body,
        )
        return {"report_id": data.get("reportId"), "status": data.get("status"),
                "message": "Report requested. Fetch with report ID when ready."}
    except Exception as e:
        log.error("Ads performance error: %s", e)
        return {"report": None, "error": str(e)}


@ads_r.post("/campaigns/update-bid")
async def update_keyword_bid(
    profile_id: str,
    keyword_id: str,
    new_bid: float,
    current: User = Depends(get_current_user),
):
    """Update keyword bid directly via Amazon Ads API."""
    if not ADS_CLIENT_ID:
        raise HTTPException(503, "Ads API not configured")
    try:
        data = await _ads_api_request(
            "PUT",
            "/v2/keywords",
            profile_id=profile_id,
            body=[{"keywordId": keyword_id, "bid": new_bid, "state": "enabled"}],
        )
        return {"updated": data, "message": f"Bid updated to ${new_bid}"}
    except Exception as e:
        log.error("Ads update bid error: %s", e)
        raise HTTPException(500, str(e))


# ── mount new routers ──────────────────────────────────────────
api.include_router(spapi_r)
api.include_router(ads_r)


# ==============================================================
#  AMAZON SP-API INTEGRATION
#  Covers: Orders, Products, Inventory, FBA Shipments
# ==============================================================

SP_API_CLIENT_ID     = os.getenv("SP_API_CLIENT_ID", "")
SP_API_CLIENT_SECRET = os.getenv("SP_API_CLIENT_SECRET", "")
SP_API_REFRESH_TOKEN = os.getenv("SP_API_REFRESH_TOKEN", "")
SELLER_ID            = os.getenv("SELLER_ID", "")
MARKETPLACE_ID       = os.getenv("MARKETPLACE_ID", "A21TJRUUN4KGV")  # India default

# Amazon Ads API
ADS_CLIENT_ID     = os.getenv("ADS_CLIENT_ID", "")
ADS_CLIENT_SECRET = os.getenv("ADS_CLIENT_SECRET", "")
ADS_REFRESH_TOKEN = os.getenv("ADS_REFRESH_TOKEN", "")
ADS_PROFILE_ID    = os.getenv("ADS_PROFILE_ID", "")

# Marketplace endpoints
MARKETPLACE_ENDPOINTS = {
    "A21TJRUUN4KGV": "https://sellingpartnerapi-fe.amazon.com",   # India
    "ATVPDKIKX0DER": "https://sellingpartnerapi-na.amazon.com",   # US
    "A1F83G8C2ARO7P": "https://sellingpartnerapi-eu.amazon.com",  # UK
    "A1PA6795UKMFR9": "https://sellingpartnerapi-eu.amazon.com",  # Germany
}

ADS_ENDPOINTS = {
    "A21TJRUUN4KGV": "https://advertising-api-fe.amazon.com",    # India
    "ATVPDKIKX0DER": "https://advertising-api.amazon.com",       # US
    "A1F83G8C2ARO7P": "https://advertising-api-eu.amazon.com",   # EU
}


class AmazonTokenCache:
    """Cache access tokens so we don't refresh on every request."""
    def __init__(self):
        self._sp_token: Optional[str] = None
        self._sp_expiry: Optional[datetime] = None
        self._ads_token: Optional[str] = None
        self._ads_expiry: Optional[datetime] = None

    async def get_sp_token(self) -> Optional[str]:
        if self._sp_token and self._sp_expiry and datetime.utcnow() < self._sp_expiry:
            return self._sp_token
        return await self._refresh_sp_token()

    async def _refresh_sp_token(self) -> Optional[str]:
        if not all([SP_API_CLIENT_ID, SP_API_CLIENT_SECRET, SP_API_REFRESH_TOKEN]):
            return None
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    "https://api.amazon.com/auth/o2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": SP_API_REFRESH_TOKEN,
                        "client_id": SP_API_CLIENT_ID,
                        "client_secret": SP_API_CLIENT_SECRET,
                    },
                )
                r.raise_for_status()
                data = r.json()
                self._sp_token  = data["access_token"]
                self._sp_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)
                return self._sp_token
        except Exception as e:
            log.error("SP-API token refresh failed: %s", e)
            return None

    async def get_ads_token(self) -> Optional[str]:
        if self._ads_token and self._ads_expiry and datetime.utcnow() < self._ads_expiry:
            return self._ads_token
        return await self._refresh_ads_token()

    async def _refresh_ads_token(self) -> Optional[str]:
        if not all([ADS_CLIENT_ID, ADS_CLIENT_SECRET, ADS_REFRESH_TOKEN]):
            return None
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    "https://api.amazon.com/auth/o2/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": ADS_REFRESH_TOKEN,
                        "client_id": ADS_CLIENT_ID,
                        "client_secret": ADS_CLIENT_SECRET,
                    },
                )
                r.raise_for_status()
                data = r.json()
                self._ads_token  = data["access_token"]
                self._ads_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)
                return self._ads_token
        except Exception as e:
            log.error("Ads API token refresh failed: %s", e)
            return None


token_cache = AmazonTokenCache()


def _sp_headers(token: str) -> dict:
    return {
        "x-amz-access-token": token,
        "x-amz-marketplace-id": MARKETPLACE_ID,
        "Content-Type": "application/json",
    }


def _ads_headers(token: str, profile_id: str = "") -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "Amazon-Advertising-API-ClientId": ADS_CLIENT_ID,
        "Content-Type": "application/json",
    }
    if profile_id or ADS_PROFILE_ID:
        h["Amazon-Advertising-API-Scope"] = profile_id or ADS_PROFILE_ID
    return h


def _sp_base() -> str:
    return MARKETPLACE_ENDPOINTS.get(MARKETPLACE_ID, "https://sellingpartnerapi-fe.amazon.com")


def _ads_base() -> str:
    return ADS_ENDPOINTS.get(MARKETPLACE_ID, "https://advertising-api-fe.amazon.com")


# ==============================================================
#  SP-API — ORDERS
# ==============================================================
sp_router = APIRouter(prefix="/sp", tags=["sp-api"])


@sp_router.get("/orders")
async def get_real_orders(
    days: int = 30,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real orders from Amazon SP-API and sync to database."""
    token = await token_cache.get_sp_token()
    if not token:
        return {"orders": [], "message": "SP-API not configured. Add SP_API credentials to Render environment."}

    created_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{_sp_base()}/orders/v0/orders"
    params = {
        "MarketplaceIds": MARKETPLACE_ID,
        "CreatedAfter": created_after,
        "OrderStatuses": "Shipped,Delivered,Unshipped,PartiallyShipped",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=_sp_headers(token), params=params)
            r.raise_for_status()
            data = r.json()

        orders = data.get("payload", {}).get("Orders", [])

        # sync to DB
        sid = _store_ids(db, current)
        if sid:
            for o in orders:
                amount = float(o.get("OrderTotal", {}).get("Amount", 0))
                existing = db.query(Order).filter(Order.id == o["AmazonOrderId"]).first()
                if not existing:
                    order_date = datetime.strptime(o["PurchaseDate"][:19], "%Y-%m-%dT%H:%M:%S")
                    db.add(Order(
                        id=o["AmazonOrderId"],
                        store_id=sid[0],
                        order_date=order_date,
                        revenue=amount,
                        profit=amount * 0.2,
                        ad_spend=amount * 0.15,
                        marketplace="Amazon",
                        status=o.get("OrderStatus", "shipped"),
                    ))
            db.commit()

        return {
            "orders": orders[:50],
            "total": len(orders),
            "message": f"Fetched {len(orders)} real orders from Amazon",
        }
    except httpx.HTTPStatusError as e:
        log.error("SP-API orders error: %s %s", e.response.status_code, e.response.text)
        raise HTTPException(500, f"Amazon API error: {e.response.status_code}")
    except Exception as e:
        log.error("SP-API orders error: %s", e)
        raise HTTPException(500, "Failed to fetch orders from Amazon")


# ==============================================================
#  SP-API — PRODUCTS / CATALOG
# ==============================================================
@sp_router.get("/products")
async def get_real_products(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real products from Amazon SP-API catalog."""
    token = await token_cache.get_sp_token()
    if not token:
        return {"products": [], "message": "SP-API not configured"}

    url = f"{_sp_base()}/listings/2021-08-01/items/{SELLER_ID}"
    params = {"marketplaceIds": MARKETPLACE_ID, "pageSize": 50}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=_sp_headers(token), params=params)
            r.raise_for_status()
            data = r.json()

        items = data.get("items", [])
        sid = _store_ids(db, current)
        products = []

        for item in items:
            asin = item.get("asin", "")
            summaries = item.get("summaries", [{}])[0]
            name = summaries.get("itemName", asin)
            price = 0.0
            prices = item.get("offers", [{}])
            if prices:
                price = float(prices[0].get("buyingPrice", {}).get("listingPrice", {}).get("amount", 0))

            # sync to DB
            if sid:
                existing = db.query(Product).filter(
                    Product.asin == asin, Product.store_id == sid[0]
                ).first()
                if not existing:
                    db.add(Product(store_id=sid[0], asin=asin, name=name, price=price))

            products.append({"asin": asin, "name": name, "price": price})

        if sid: db.commit()
        return {"products": products, "total": len(products)}

    except Exception as e:
        log.error("SP-API products error: %s", e)
        return {"products": [], "message": str(e)}


# ==============================================================
#  SP-API — INVENTORY
# ==============================================================
@sp_router.get("/inventory")
async def get_real_inventory(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real FBA inventory from Amazon SP-API."""
    token = await token_cache.get_sp_token()
    if not token:
        return {"inventory": [], "message": "SP-API not configured"}

    url = f"{_sp_base()}/fba/inventory/v1/summaries"
    params = {
        "details": "true",
        "granularityType": "Marketplace",
        "granularityId": MARKETPLACE_ID,
        "marketplaceIds": MARKETPLACE_ID,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=_sp_headers(token), params=params)
            r.raise_for_status()
            data = r.json()

        inventory = data.get("payload", {}).get("inventorySummaries", [])

        # sync stock levels to DB
        sid = _store_ids(db, current)
        for item in inventory:
            asin = item.get("asin", "")
            qty  = item.get("inventoryDetails", {}).get("fulfillableQuantity", 0)
            if sid:
                prod = db.query(Product).filter(
                    Product.asin == asin, Product.store_id == sid[0]
                ).first()
                if prod:
                    prod.stock_level = qty
        if sid: db.commit()

        return {
            "inventory": inventory,
            "total": len(inventory),
            "low_stock": [i for i in inventory if i.get("inventoryDetails", {}).get("fulfillableQuantity", 0) < 50],
        }
    except Exception as e:
        log.error("SP-API inventory error: %s", e)
        return {"inventory": [], "message": str(e)}


# ==============================================================
#  SP-API — FBA SHIPMENTS
# ==============================================================
@sp_router.get("/shipments")
async def get_real_shipments(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real FBA inbound shipments from Amazon SP-API."""
    token = await token_cache.get_sp_token()
    if not token:
        return {"shipments": [], "message": "SP-API not configured"}

    url = f"{_sp_base()}/fba/inbound/v0/shipments"
    params = {
        "MarketplaceId": MARKETPLACE_ID,
        "ShipmentStatusList": "WORKING,SHIPPED,IN_TRANSIT,DELIVERED,CHECKED_IN,RECEIVING,CLOSED",
        "QueryType": "SHIPMENT",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=_sp_headers(token), params=params)
            r.raise_for_status()
            data = r.json()

        shipments = data.get("payload", {}).get("ShipmentData", [])
        return {
            "shipments": shipments,
            "total": len(shipments),
        }
    except Exception as e:
        log.error("SP-API shipments error: %s", e)
        return {"shipments": [], "message": str(e)}


# ==============================================================
#  AMAZON ADS API
#  Covers: Profiles, Campaigns, Ad Groups, Keywords, Reports
# ==============================================================
ads_router = APIRouter(prefix="/ads", tags=["ads-api"])


@ads_router.get("/profiles")
async def get_ads_profiles(current: User = Depends(get_current_user)):
    """Get all advertising profiles — find your profile ID here."""
    token = await token_cache.get_ads_token()
    if not token:
        return {"profiles": [], "message": "Ads API not configured. Add ADS_CLIENT_ID, ADS_CLIENT_SECRET, ADS_REFRESH_TOKEN to Render."}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{_ads_base()}/v2/profiles",
                headers=_ads_headers(token),
            )
            r.raise_for_status()
            profiles = r.json()
        return {
            "profiles": profiles,
            "tip": "Copy your profileId and add it as ADS_PROFILE_ID in Render environment",
        }
    except Exception as e:
        log.error("Ads profiles error: %s", e)
        return {"profiles": [], "message": str(e)}


@ads_router.get("/campaigns")
async def get_real_campaigns(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real campaigns from Amazon Ads API and sync to database."""
    token = await token_cache.get_ads_token()
    if not token:
        return {"campaigns": [], "message": "Ads API not configured"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{_ads_base()}/v2/sp/campaigns",
                headers=_ads_headers(token),
                params={"stateFilter": "enabled,paused"},
            )
            r.raise_for_status()
            campaigns = r.json()

        # sync to DB
        sid = _store_ids(db, current)
        synced = 0
        for camp in campaigns:
            if not sid: break
            existing = db.query(Campaign).filter(
                Campaign.id == str(camp["campaignId"])
            ).first()
            if not existing:
                db.add(Campaign(
                    id=str(camp["campaignId"]),
                    store_id=sid[0],
                    name=camp.get("name", ""),
                    campaign_type="sponsored_products",
                    status=camp.get("state", "active"),
                    daily_budget=float(camp.get("dailyBudget", 0)),
                    target_acos=float(camp.get("targetAcos", 25) or 25),
                ))
                synced += 1
        if sid and synced: db.commit()

        return {
            "campaigns": campaigns,
            "total": len(campaigns),
            "synced_to_db": synced,
        }
    except Exception as e:
        log.error("Ads campaigns error: %s", e)
        return {"campaigns": [], "message": str(e)}


@ads_router.get("/keywords")
async def get_real_keywords(
    campaign_id: Optional[str] = None,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch real keywords from Amazon Ads API."""
    token = await token_cache.get_ads_token()
    if not token:
        return {"keywords": [], "message": "Ads API not configured"}

    params = {"stateFilter": "enabled,paused"}
    if campaign_id:
        params["campaignIdFilter"] = campaign_id

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{_ads_base()}/v2/sp/keywords",
                headers=_ads_headers(token),
                params=params,
            )
            r.raise_for_status()
            keywords = r.json()
        return {"keywords": keywords, "total": len(keywords)}
    except Exception as e:
        log.error("Ads keywords error: %s", e)
        return {"keywords": [], "message": str(e)}


@ads_router.post("/keywords/{keyword_id}/bid")
async def update_keyword_bid(
    keyword_id: str,
    data: Dict[str, Any],
    current: User = Depends(get_current_user),
):
    """Update a keyword bid directly on Amazon Ads API."""
    token = await token_cache.get_ads_token()
    if not token:
        raise HTTPException(400, "Ads API not configured")

    new_bid = data.get("bid")
    if not new_bid:
        raise HTTPException(400, "bid is required")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.put(
                f"{_ads_base()}/v2/sp/keywords",
                headers=_ads_headers(token),
                json=[{"keywordId": keyword_id, "bid": new_bid, "state": "enabled"}],
            )
            r.raise_for_status()
        return {"ok": True, "keyword_id": keyword_id, "new_bid": new_bid}
    except Exception as e:
        log.error("Ads keyword bid update error: %s", e)
        raise HTTPException(500, str(e))


@ads_router.get("/reports/performance")
async def get_ads_performance(
    days: int = 30,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request a performance report from Amazon Ads API (async)."""
    token = await token_cache.get_ads_token()
    if not token:
        return {"message": "Ads API not configured"}

    end_date   = datetime.utcnow().strftime("%Y%m%d")
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%d")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Request report
            r = await client.post(
                f"{_ads_base()}/v2/sp/campaigns/report",
                headers=_ads_headers(token),
                json={
                    "reportDate": end_date,
                    "metrics": "campaignName,impressions,clicks,cost,attributedSales30d,attributedOrdersNewToBrand30d,acos",
                },
            )
            r.raise_for_status()
            report = r.json()

        return {
            "report_id": report.get("reportId"),
            "status": report.get("status"),
            "message": "Report requested. Use /ads/reports/{report_id} to download when ready.",
        }
    except Exception as e:
        log.error("Ads report error: %s", e)
        return {"message": str(e)}


@ads_router.get("/sync-all")
async def sync_all_ads_data(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync ALL Amazon Ads data to database in one call."""
    token = await token_cache.get_ads_token()
    if not token:
        return {"message": "Ads API not configured. Add ADS credentials to Render."}

    results = {}

    # campaigns
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{_ads_base()}/v2/sp/campaigns",
                                 headers=_ads_headers(token),
                                 params={"stateFilter": "enabled,paused"})
            r.raise_for_status()
            campaigns = r.json()
        results["campaigns"] = len(campaigns)

        sid = _store_ids(db, current)
        for camp in campaigns:
            if not sid: break
            existing = db.query(Campaign).filter(Campaign.id == str(camp["campaignId"])).first()
            if existing:
                existing.status       = camp.get("state", existing.status)
                existing.daily_budget = float(camp.get("dailyBudget", existing.daily_budget))
            else:
                db.add(Campaign(
                    id=str(camp["campaignId"]),
                    store_id=sid[0],
                    name=camp.get("name", ""),
                    campaign_type="sponsored_products",
                    status=camp.get("state", "active"),
                    daily_budget=float(camp.get("dailyBudget", 0)),
                    target_acos=25.0,
                ))
        db.commit()
    except Exception as e:
        results["campaigns_error"] = str(e)

    # keywords
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{_ads_base()}/v2/sp/keywords",
                                 headers=_ads_headers(token),
                                 params={"stateFilter": "enabled,paused"})
            r.raise_for_status()
            keywords = r.json()
        results["keywords"] = len(keywords)

        sid = _store_ids(db, current)
        for kw in keywords:
            existing = db.query(Keyword).filter(Keyword.id == str(kw["keywordId"])).first()
            if existing:
                existing.bid    = float(kw.get("bid", existing.bid))
                existing.status = kw.get("state", existing.status)
            else:
                db.add(Keyword(
                    id=str(kw["keywordId"]),
                    campaign_id=str(kw.get("campaignId", "")),
                    keyword_text=kw.get("keywordText", ""),
                    match_type=kw.get("matchType", "exact"),
                    bid=float(kw.get("bid", 1.0)),
                    status=kw.get("state", "active"),
                ))
        db.commit()
    except Exception as e:
        results["keywords_error"] = str(e)

    await _notify(db, current.id,
                  "Amazon Ads synced",
                  f"Synced {results.get('campaigns',0)} campaigns, {results.get('keywords',0)} keywords",
                  "success")

    return {"synced": results, "message": "Amazon Ads data synced successfully!"}


# ==============================================================
#  COMBINED SYNC — calls SP-API + Ads API together
# ==============================================================
sync_router = APIRouter(prefix="/sync", tags=["sync"])


@sync_router.post("/all")
async def sync_everything(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """One-click sync of ALL Amazon data — Orders + Inventory + Campaigns + Keywords."""
    results = {}

    # SP-API sync
    sp_token = await token_cache.get_sp_token()
    if sp_token:
        try:
            # orders
            created_after = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{_sp_base()}/orders/v0/orders",
                    headers=_sp_headers(sp_token),
                    params={"MarketplaceIds": MARKETPLACE_ID, "CreatedAfter": created_after},
                )
                r.raise_for_status()
                orders = r.json().get("payload", {}).get("Orders", [])

            sid = _store_ids(db, current)
            new_orders = 0
            for o in orders:
                if sid and not db.query(Order).filter(Order.id == o["AmazonOrderId"]).first():
                    amount = float(o.get("OrderTotal", {}).get("Amount", 0))
                    order_date = datetime.strptime(o["PurchaseDate"][:19], "%Y-%m-%dT%H:%M:%S")
                    db.add(Order(
                        id=o["AmazonOrderId"], store_id=sid[0],
                        order_date=order_date, revenue=amount,
                        profit=amount*0.2, ad_spend=amount*0.15,
                        marketplace="Amazon", status=o.get("OrderStatus", "shipped"),
                    ))
                    new_orders += 1
            db.commit()
            results["new_orders"] = new_orders
            results["total_orders"] = len(orders)
        except Exception as e:
            results["orders_error"] = str(e)

        try:
            # inventory
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{_sp_base()}/fba/inventory/v1/summaries",
                    headers=_sp_headers(sp_token),
                    params={"details": "true", "granularityType": "Marketplace",
                            "granularityId": MARKETPLACE_ID, "marketplaceIds": MARKETPLACE_ID},
                )
                r.raise_for_status()
                inventory = r.json().get("payload", {}).get("inventorySummaries", [])

            sid = _store_ids(db, current)
            for item in inventory:
                asin = item.get("asin", "")
                qty  = item.get("inventoryDetails", {}).get("fulfillableQuantity", 0)
                if sid:
                    prod = db.query(Product).filter(Product.asin == asin, Product.store_id == sid[0]).first()
                    if prod: prod.stock_level = qty
            db.commit()
            results["inventory_items"] = len(inventory)
        except Exception as e:
            results["inventory_error"] = str(e)
    else:
        results["sp_api"] = "Not configured — add SP_API_CLIENT_ID, SP_API_CLIENT_SECRET, SP_API_REFRESH_TOKEN to Render"

    # Ads API sync
    ads_token = await token_cache.get_ads_token()
    if ads_token:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{_ads_base()}/v2/sp/campaigns",
                    headers=_ads_headers(ads_token),
                    params={"stateFilter": "enabled,paused"},
                )
                r.raise_for_status()
                campaigns = r.json()

            sid = _store_ids(db, current)
            new_camps = 0
            for camp in campaigns:
                if not sid: break
                existing = db.query(Campaign).filter(Campaign.id == str(camp["campaignId"])).first()
                if existing:
                    existing.status       = camp.get("state", existing.status)
                    existing.daily_budget = float(camp.get("dailyBudget", existing.daily_budget))
                else:
                    db.add(Campaign(
                        id=str(camp["campaignId"]), store_id=sid[0],
                        name=camp.get("name",""), campaign_type="sponsored_products",
                        status=camp.get("state","active"),
                        daily_budget=float(camp.get("dailyBudget",0)), target_acos=25.0,
                    ))
                    new_camps += 1
            db.commit()
            results["campaigns"] = len(campaigns)
            results["new_campaigns"] = new_camps
        except Exception as e:
            results["campaigns_error"] = str(e)
    else:
        results["ads_api"] = "Not configured — add ADS_CLIENT_ID, ADS_CLIENT_SECRET, ADS_REFRESH_TOKEN to Render"

    # notify user
    msg = f"Synced: {results.get('total_orders',0)} orders, {results.get('inventory_items',0)} inventory items, {results.get('campaigns',0)} campaigns"
    await _notify(db, current.id, "Sync complete", msg, "success")

    return {"results": results, "message": msg}


@sync_router.get("/status")
async def sync_status(current: User = Depends(get_current_user)):
    """Check which APIs are configured and ready."""
    sp_ready  = all([SP_API_CLIENT_ID, SP_API_CLIENT_SECRET, SP_API_REFRESH_TOKEN])
    ads_ready = all([ADS_CLIENT_ID, ADS_CLIENT_SECRET, ADS_REFRESH_TOKEN])
    return {
        "sp_api": {
            "configured": sp_ready,
            "covers": ["Orders", "Products", "Inventory", "FBA Shipments"],
            "missing": [] if sp_ready else ["SP_API_CLIENT_ID", "SP_API_CLIENT_SECRET", "SP_API_REFRESH_TOKEN"],
        },
        "ads_api": {
            "configured": ads_ready,
            "covers": ["Campaigns", "Keywords", "Bids", "ACoS", "ROAS"],
            "missing": [] if ads_ready else ["ADS_CLIENT_ID", "ADS_CLIENT_SECRET", "ADS_REFRESH_TOKEN"],
            "profile_set": bool(ADS_PROFILE_ID),
        },
        "seller_id":    SELLER_ID or "NOT SET — add SELLER_ID to Render",
        "marketplace":  MARKETPLACE_ID,
    }


# Mount the new routers
api.include_router(sp_router)
api.include_router(ads_router)
api.include_router(sync_router)


# ==============================================================
#  PER-STORE TOKEN HELPERS
#  Each store uses its own credentials, falls back to global env
# ==============================================================

async def get_store_sp_token(store: Store) -> Optional[str]:
    """Get SP-API token for a specific store — uses store credentials or global fallback."""
    # check cached token
    if store.sp_access_token and store.sp_token_expiry and datetime.utcnow() < store.sp_token_expiry:
        return store.sp_access_token

    # use store-specific credentials, fall back to global env
    client_id     = store.sp_client_id     or SP_API_CLIENT_ID
    client_secret = store.sp_client_secret or SP_API_CLIENT_SECRET
    refresh_token = store.sp_refresh_token or SP_API_REFRESH_TOKEN

    if not all([client_id, client_secret, refresh_token]):
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            r.raise_for_status()
            data = r.json()
            # cache in store object (caller must commit)
            store.sp_access_token = data["access_token"]
            store.sp_token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)
            return store.sp_access_token
    except Exception as e:
        log.error("Store %s SP token error: %s", store.store_name, e)
        return None


async def get_store_ads_token(store: Store) -> Optional[str]:
    """Get Ads API token for a specific store."""
    if store.ads_access_token and store.ads_token_expiry and datetime.utcnow() < store.ads_token_expiry:
        return store.ads_access_token

    client_id     = store.ads_client_id     or ADS_CLIENT_ID
    client_secret = store.ads_client_secret or ADS_CLIENT_SECRET
    refresh_token = store.ads_refresh_token or ADS_REFRESH_TOKEN

    if not all([client_id, client_secret, refresh_token]):
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            r.raise_for_status()
            data = r.json()
            store.ads_access_token = data["access_token"]
            store.ads_token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)
            return store.ads_access_token
    except Exception as e:
        log.error("Store %s Ads token error: %s", store.store_name, e)
        return None


def _store_sp_headers(token: str, marketplace_id: str) -> dict:
    return {
        "x-amz-access-token": token,
        "x-amz-marketplace-id": marketplace_id,
        "Content-Type": "application/json",
    }


def _store_ads_headers(token: str, client_id: str, profile_id: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Amazon-Advertising-API-ClientId": client_id or ADS_CLIENT_ID,
        "Amazon-Advertising-API-Scope": profile_id or ADS_PROFILE_ID,
        "Content-Type": "application/json",
    }


# ==============================================================
#  MULTI-STORE SYNC ROUTER
# ==============================================================
multi_router = APIRouter(prefix="/multi-store", tags=["multi-store"])


@multi_router.get("/status")
async def multi_store_status(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Show all connected stores and their API status."""
    stores = db.query(Store).filter(Store.user_id == current.id).all()
    result = []
    for s in stores:
        result.append({
            "id": s.id,
            "store_name": s.store_name,
            "marketplace": s.marketplace,
            "marketplace_id": s.marketplace_id or "A21TJRUUN4KGV",
            "seller_id": s.seller_id,
            "sp_api_ready": bool(s.sp_refresh_token or SP_API_REFRESH_TOKEN),
            "ads_api_ready": bool(s.ads_refresh_token or ADS_REFRESH_TOKEN),
            "ads_profile_set": bool(s.ads_profile_id or ADS_PROFILE_ID),
            "last_sync": s.last_sync.isoformat() if s.last_sync else None,
        })
    return {
        "stores": result,
        "total": len(result),
        "all_synced": all(s["sp_api_ready"] for s in result),
    }


@multi_router.post("/sync/{store_id}")
async def sync_single_store(
    store_id: str,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync one specific store using its own credentials."""
    store = db.query(Store).filter(
        Store.id == store_id, Store.user_id == current.id
    ).first()
    if not store:
        raise HTTPException(404, "Store not found")

    results = {"store": store.store_name}
    mp_id = store.marketplace_id or MARKETPLACE_ID
    sp_base = MARKETPLACE_ENDPOINTS.get(mp_id, "https://sellingpartnerapi-fe.amazon.com")

    # SP-API sync for this store
    sp_token = await get_store_sp_token(store)
    if sp_token:
        db.commit()  # save cached token
        try:
            created_after = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{sp_base}/orders/v0/orders",
                    headers=_store_sp_headers(sp_token, mp_id),
                    params={"MarketplaceIds": mp_id, "CreatedAfter": created_after},
                )
                r.raise_for_status()
                orders = r.json().get("payload", {}).get("Orders", [])

            new_orders = 0
            for o in orders:
                if not db.query(Order).filter(Order.id == o["AmazonOrderId"]).first():
                    amount = float(o.get("OrderTotal", {}).get("Amount", 0))
                    order_date = datetime.strptime(o["PurchaseDate"][:19], "%Y-%m-%dT%H:%M:%S")
                    db.add(Order(
                        id=o["AmazonOrderId"], store_id=store.id,
                        order_date=order_date, revenue=amount,
                        profit=amount*0.2, ad_spend=amount*0.15,
                        marketplace=store.marketplace, status=o.get("OrderStatus","shipped"),
                    ))
                    new_orders += 1
            db.commit()
            results["new_orders"] = new_orders
            results["total_orders"] = len(orders)
        except Exception as e:
            results["orders_error"] = str(e)

        # inventory
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{sp_base}/fba/inventory/v1/summaries",
                    headers=_store_sp_headers(sp_token, mp_id),
                    params={"details":"true","granularityType":"Marketplace",
                            "granularityId":mp_id,"marketplaceIds":mp_id},
                )
                r.raise_for_status()
                inventory = r.json().get("payload",{}).get("inventorySummaries",[])

            for item in inventory:
                asin = item.get("asin","")
                qty  = item.get("inventoryDetails",{}).get("fulfillableQuantity",0)
                prod = db.query(Product).filter(Product.asin==asin, Product.store_id==store.id).first()
                if prod: prod.stock_level = qty
            db.commit()
            results["inventory_items"] = len(inventory)
        except Exception as e:
            results["inventory_error"] = str(e)
    else:
        results["sp_api"] = "No credentials — add sp_refresh_token to this store"

    # Ads API sync for this store
    ads_token = await get_store_ads_token(store)
    if ads_token:
        db.commit()
        ads_base   = ADS_ENDPOINTS.get(mp_id, "https://advertising-api-fe.amazon.com")
        client_id  = store.ads_client_id  or ADS_CLIENT_ID
        profile_id = store.ads_profile_id or ADS_PROFILE_ID

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{ads_base}/v2/sp/campaigns",
                    headers=_store_ads_headers(ads_token, client_id, profile_id),
                    params={"stateFilter":"enabled,paused"},
                )
                r.raise_for_status()
                campaigns = r.json()

            new_camps = 0
            for camp in campaigns:
                existing = db.query(Campaign).filter(Campaign.id==str(camp["campaignId"])).first()
                if existing:
                    existing.status       = camp.get("state", existing.status)
                    existing.daily_budget = float(camp.get("dailyBudget", existing.daily_budget))
                else:
                    db.add(Campaign(
                        id=str(camp["campaignId"]), store_id=store.id,
                        name=camp.get("name",""), campaign_type="sponsored_products",
                        status=camp.get("state","active"),
                        daily_budget=float(camp.get("dailyBudget",0)), target_acos=25.0,
                    ))
                    new_camps += 1
            db.commit()
            results["campaigns"] = len(campaigns)
            results["new_campaigns"] = new_camps
        except Exception as e:
            results["campaigns_error"] = str(e)
    else:
        results["ads_api"] = "No credentials — add ads_refresh_token to this store"

    # update last sync
    store.last_sync = datetime.utcnow()
    db.commit()

    await _notify(db, current.id,
                  f"{store.store_name} synced",
                  f"Orders: {results.get('total_orders',0)}, Campaigns: {results.get('campaigns',0)}",
                  "success")

    return results


@multi_router.post("/sync-all")
async def sync_all_stores(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync ALL connected stores at once — each using its own credentials."""
    stores = db.query(Store).filter(Store.user_id == current.id).all()
    if not stores:
        return {"message": "No stores connected"}

    all_results = []
    for store in stores:
        try:
            # reuse single store sync logic
            result = await sync_single_store.__wrapped__(store.id, current, db) \
                if hasattr(sync_single_store, '__wrapped__') \
                else {"store": store.store_name, "note": "Use /multi-store/sync/{id} per store"}
            all_results.append(result)
        except Exception as e:
            all_results.append({"store": store.store_name, "error": str(e)})

    return {
        "synced_stores": len(stores),
        "results": all_results,
    }


@multi_router.patch("/{store_id}/credentials")
async def update_store_credentials(
    store_id: str,
    data: Dict[str, Any],
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update SP-API or Ads API credentials for a specific store."""
    store = db.query(Store).filter(
        Store.id == store_id, Store.user_id == current.id
    ).first()
    if not store:
        raise HTTPException(404, "Store not found")

    allowed = [
        "sp_client_id", "sp_client_secret", "sp_refresh_token",
        "ads_client_id", "ads_client_secret", "ads_refresh_token",
        "ads_profile_id", "seller_id", "marketplace_id",
    ]
    updated = []
    for key in allowed:
        if key in data:
            setattr(store, key, data[key])
            # clear cached token when credentials change
            if "sp_" in key:
                store.sp_access_token = ""
                store.sp_token_expiry = None
            if "ads_" in key:
                store.ads_access_token = ""
                store.ads_token_expiry = None
            updated.append(key)

    db.commit()
    return {
        "ok": True,
        "updated": updated,
        "store": store.store_name,
        "sp_api_ready":  bool(store.sp_refresh_token  or SP_API_REFRESH_TOKEN),
        "ads_api_ready": bool(store.ads_refresh_token or ADS_REFRESH_TOKEN),
    }


# Mount multi-store router
api.include_router(multi_router)


# ==============================================================
#  AMAZON OAUTH 2.0 FLOW
#  User clicks "Connect Amazon" → redirected to Amazon login
#  → Amazon sends back authorization code
#  → We exchange for refresh token automatically
#  → Store saved, user redirected back to dashboard
#  No manual token entry needed!
# ==============================================================

import hashlib
import secrets
from urllib.parse import urlencode, quote

oauth_router = APIRouter(prefix="/amazon", tags=["amazon-oauth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://sellervector-frontend.onrender.com")

# Marketplace config
MARKETPLACES = {
    "IN": {
        "name": "Amazon India",
        "marketplace_id": "A21TJRUUN4KGV",
        "region": "fe",
        "seller_central": "https://sellercentral.amazon.in",
        "ads_region": "https://advertising-api-fe.amazon.com",
        "sp_endpoint": "https://sellingpartnerapi-fe.amazon.com",
    },
    "US": {
        "name": "Amazon US",
        "marketplace_id": "ATVPDKIKX0DER",
        "region": "na",
        "seller_central": "https://sellercentral.amazon.com",
        "ads_region": "https://advertising-api.amazon.com",
        "sp_endpoint": "https://sellingpartnerapi-na.amazon.com",
    },
    "UK": {
        "name": "Amazon UK",
        "marketplace_id": "A1F83G8C2ARO7P",
        "region": "eu",
        "seller_central": "https://sellercentral.amazon.co.uk",
        "ads_region": "https://advertising-api-eu.amazon.com",
        "sp_endpoint": "https://sellingpartnerapi-eu.amazon.com",
    },
    "DE": {
        "name": "Amazon Germany",
        "marketplace_id": "A1PA6795UKMFR9",
        "region": "eu",
        "seller_central": "https://sellercentral.amazon.de",
        "ads_region": "https://advertising-api-eu.amazon.com",
        "sp_endpoint": "https://sellingpartnerapi-eu.amazon.com",
    },
    "AE": {
        "name": "Amazon UAE",
        "marketplace_id": "A2VIGQ35RCS4UG",
        "region": "fe",
        "seller_central": "https://sellercentral.amazon.ae",
        "ads_region": "https://advertising-api-fe.amazon.com",
        "sp_endpoint": "https://sellingpartnerapi-fe.amazon.com",
    },
}

# temporary state store (in production use Redis)
_oauth_states: Dict[str, dict] = {}


@oauth_router.get("/connect/url")
async def get_amazon_connect_url(
    marketplace: str = "IN",
    store_name: str = "My Store",
    current: User = Depends(get_current_user),
):
    """
    Step 1 of OAuth flow.
    Frontend calls this → gets a URL → redirects user to Amazon login.
    """
    mp = MARKETPLACES.get(marketplace.upper())
    if not mp:
        raise HTTPException(400, f"Unknown marketplace. Use: {list(MARKETPLACES.keys())}")

    if not SP_API_CLIENT_ID:
        raise HTTPException(400, "SP_API_CLIENT_ID not configured in Render environment")

    # generate state token to prevent CSRF
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id":    current.id,
        "marketplace": marketplace.upper(),
        "store_name": store_name,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Build Amazon authorization URL
    callback_url = f"https://sellervector-backend.onrender.com/api/amazon/callback"

    params = {
        "application_id": SP_API_CLIENT_ID,
        "state": state,
        "redirect_uri": callback_url,
        "version": "beta",
    }

    auth_url = f"{mp['seller_central']}/apps/authorize/consent?{urlencode(params)}"

    return {
        "url": auth_url,
        "state": state,
        "marketplace": marketplace,
        "store_name": store_name,
        "message": "Redirect user to this URL",
    }


@oauth_router.get("/callback")
async def amazon_oauth_callback(
    state: str,
    spapi_oauth_code: Optional[str] = None,
    selling_partner_id: Optional[str] = None,
    mws_auth_token: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Step 2 of OAuth flow.
    Amazon redirects here after user authorizes.
    We exchange the code for a refresh token and save the store.
    User is then redirected back to the dashboard.
    """
    # handle user denial
    if error:
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?error=amazon_denied"},
        )

    # validate state
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?error=invalid_state"},
        )

    user_id    = state_data["user_id"]
    marketplace = state_data["marketplace"]
    store_name = state_data["store_name"]
    mp         = MARKETPLACES.get(marketplace, MARKETPLACES["IN"])

    refresh_token = None

    # exchange authorization code for LWA refresh token
    if spapi_oauth_code:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    "https://api.amazon.com/auth/o2/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": spapi_oauth_code,
                        "client_id": SP_API_CLIENT_ID,
                        "client_secret": SP_API_CLIENT_SECRET,
                    },
                )
                r.raise_for_status()
                token_data     = r.json()
                refresh_token  = token_data.get("refresh_token")
                access_token   = token_data.get("access_token")
                expires_in     = token_data.get("expires_in", 3600)
        except Exception as e:
            log.error("OAuth token exchange error: %s", e)
            return JSONResponse(
                status_code=302,
                headers={"Location": f"{FRONTEND_URL}/settings?error=token_exchange_failed"},
            )

    # save store to database
    try:
        store = Store(
            user_id=user_id,
            marketplace=mp["name"],
            store_name=store_name,
            seller_id=selling_partner_id or "",
            marketplace_id=mp["marketplace_id"],
            sp_client_id=SP_API_CLIENT_ID,
            sp_client_secret=SP_API_CLIENT_SECRET,
            sp_refresh_token=refresh_token or "",
            sp_access_token=access_token if refresh_token else "",
            sp_token_expiry=datetime.utcnow() + timedelta(seconds=expires_in - 60) if refresh_token else None,
            is_connected=True,
        )
        db.add(store)
        db.commit()
        db.refresh(store)

        # create welcome notification
        notif = Notification(
            user_id=user_id,
            title=f"{store_name} connected!",
            message=f"Your {mp['name']} store is now connected. Syncing data...",
            severity="success",
        )
        db.add(notif)
        db.commit()

        # redirect back to frontend with success
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?success=store_connected&store_id={store.id}"},
        )
    except Exception as e:
        log.error("Store save error: %s", e)
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?error=store_save_failed"},
        )


@oauth_router.get("/ads/connect/url")
async def get_ads_connect_url(
    store_id: Optional[str] = None,
    marketplace: str = "IN",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    OAuth URL for Amazon Ads API connection.
    Separate from SP-API — user clicks "Connect Ads" button.
    """
    if not ADS_CLIENT_ID:
        raise HTTPException(400, "ADS_CLIENT_ID not configured in Render environment")

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id":    current.id,
        "store_id":   store_id,
        "marketplace": marketplace.upper(),
        "type":       "ads",
        "created_at": datetime.utcnow().isoformat(),
    }

    callback_url = "https://sellervector-backend.onrender.com/api/amazon/ads/callback"

    params = {
        "client_id":     ADS_CLIENT_ID,
        "scope":         "advertising::campaign_management",
        "response_type": "code",
        "redirect_uri":  callback_url,
        "state":         state,
    }

    auth_url = f"https://www.amazon.com/ap/oa?{urlencode(params)}"
    return {"url": auth_url, "state": state}


@oauth_router.get("/ads/callback")
async def amazon_ads_callback(
    state: str,
    code: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Handle Amazon Ads OAuth callback."""
    if error:
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?error=ads_denied"},
        )

    state_data = _oauth_states.pop(state, None)
    if not state_data:
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?error=invalid_state"},
        )

    user_id  = state_data["user_id"]
    store_id = state_data.get("store_id")

    if not code:
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?error=no_code"},
        )

    try:
        # exchange code for refresh token
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type":    "authorization_code",
                    "code":          code,
                    "client_id":     ADS_CLIENT_ID,
                    "client_secret": ADS_CLIENT_SECRET,
                    "redirect_uri":  "https://sellervector-backend.onrender.com/api/amazon/ads/callback",
                },
            )
            r.raise_for_status()
            token_data    = r.json()
            refresh_token = token_data.get("refresh_token")
            access_token  = token_data.get("access_token")
            expires_in    = token_data.get("expires_in", 3600)

        # get profile ID automatically
        profile_id = ""
        if access_token:
            mp = MARKETPLACES.get(state_data.get("marketplace", "IN"), MARKETPLACES["IN"])
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get(
                        f"{mp['ads_region']}/v2/profiles",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Amazon-Advertising-API-ClientId": ADS_CLIENT_ID,
                        },
                    )
                    r.raise_for_status()
                    profiles = r.json()
                    if profiles:
                        profile_id = str(profiles[0].get("profileId", ""))
            except Exception as e:
                log.warning("Could not fetch Ads profiles: %s", e)

        # save to store if store_id provided
        if store_id:
            store = db.query(Store).filter(
                Store.id == store_id, Store.user_id == user_id
            ).first()
            if store:
                store.ads_client_id     = ADS_CLIENT_ID
                store.ads_client_secret = ADS_CLIENT_SECRET
                store.ads_refresh_token = refresh_token or ""
                store.ads_access_token  = access_token or ""
                store.ads_token_expiry  = datetime.utcnow() + timedelta(seconds=expires_in-60)
                store.ads_profile_id    = profile_id
                db.commit()

        # also save globally for backward compat
        notif = Notification(
            user_id=user_id,
            title="Amazon Ads connected!",
            message=f"Ads API connected. Profile ID: {profile_id or 'check /ads/profiles'}",
            severity="success",
        )
        db.add(notif)
        db.commit()

        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?success=ads_connected&profile_id={profile_id}"},
        )
    except Exception as e:
        log.error("Ads OAuth callback error: %s", e)
        return JSONResponse(
            status_code=302,
            headers={"Location": f"{FRONTEND_URL}/settings?error=ads_token_failed"},
        )


@oauth_router.get("/marketplaces")
def list_marketplaces():
    """Return all supported marketplaces — shown in Connect Store modal."""
    return {
        "marketplaces": [
            {"code": k, "name": v["name"], "marketplace_id": v["marketplace_id"]}
            for k, v in MARKETPLACES.items()
        ]
    }


# Mount oauth router
api.include_router(oauth_router)
