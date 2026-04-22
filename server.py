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
FRONTEND_ORIGINS      = os.getenv("FRONTEND_ORIGINS", "*").split(",")

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
    marketplace  = Column(String, nullable=False)      # Amazon / Flipkart etc.
    store_name   = Column(String, nullable=False)
    seller_id    = Column(String, default="")
    api_token    = Column(String, default="")
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
    api_token: Optional[str] = ""


class StoreOut(BaseModel):
    id: str
    marketplace: str
    store_name: str
    seller_id: str
    is_connected: bool
    connected_at: datetime
    last_sync: Optional[datetime]
    class Config: from_attributes = True


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
    allow_credentials=True,
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
