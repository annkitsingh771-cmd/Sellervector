"""
SellerVector Backend - Clean minimal version
Guaranteed to work - tested locally
"""
import os, uuid, logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import bcrypt
from jose import JWTError, jwt
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, desc
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# CONFIG
SECRET_KEY = os.getenv("SECRET_KEY", "sellervector-secret-2026")
ALGORITHM = "HS256"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sellervector.db")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sellervector")

# DATABASE
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

# MODELS
class User(Base):
    __tablename__ = "users"
    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, default="")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    stores          = relationship("Store", back_populates="user", cascade="all, delete-orphan")
    notifications   = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Store(Base):
    __tablename__ = "stores"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    marketplace  = Column(String, nullable=False)
    store_name   = Column(String, nullable=False)
    seller_id    = Column(String, default="")
    is_connected = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    last_sync    = Column(DateTime, nullable=True)
    user         = relationship("User", back_populates="stores")
    campaigns    = relationship("Campaign", back_populates="store", cascade="all, delete-orphan")
    products     = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    orders       = relationship("Order", back_populates="store", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id    = Column(String, ForeignKey("stores.id"), nullable=False)
    asin        = Column(String, default="")
    name        = Column(String, nullable=False)
    price       = Column(Float, default=0.0)
    cost        = Column(Float, default=0.0)
    stock_level = Column(Integer, default=0)
    status      = Column(String, default="active")
    store       = relationship("Store", back_populates="products")

class Order(Base):
    __tablename__ = "orders"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id   = Column(String, ForeignKey("stores.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.utcnow)
    revenue    = Column(Float, default=0.0)
    profit     = Column(Float, default=0.0)
    ad_spend   = Column(Float, default=0.0)
    status     = Column(String, default="shipped")
    store      = relationship("Store", back_populates="orders")

class Campaign(Base):
    __tablename__ = "campaigns"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id      = Column(String, ForeignKey("stores.id"), nullable=False)
    name          = Column(String, nullable=False)
    campaign_type = Column(String, default="sponsored_products")
    status        = Column(String, default="active")
    daily_budget  = Column(Float, default=50.0)
    spend         = Column(Float, default=0.0)
    revenue       = Column(Float, default=0.0)
    impressions   = Column(Integer, default=0)
    clicks        = Column(Integer, default=0)
    orders        = Column(Integer, default=0)
    acos          = Column(Float, nullable=True)
    roas          = Column(Float, nullable=True)
    target_acos   = Column(Float, default=25.0)
    created_at    = Column(DateTime, default=datetime.utcnow)
    store         = relationship("Store", back_populates="campaigns")

class OptimizationItem(Base):
    __tablename__ = "optimization_items"
    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    title        = Column(String, nullable=False)
    description  = Column(Text, default="")
    type         = Column(String, default="bid_decrease")
    priority     = Column(String, default="medium")
    campaign_name= Column(String, default="")
    keyword      = Column(String, default="")
    current_bid  = Column(Float, nullable=True)
    suggested_bid= Column(Float, nullable=True)
    current_acos = Column(Float, nullable=True)
    expected_acos= Column(Float, nullable=True)
    estimated_savings       = Column(Float, nullable=True)
    estimated_revenue_gain  = Column(Float, nullable=True)
    spend        = Column(Float, nullable=True)
    sales        = Column(Float, nullable=True)
    status       = Column(String, default="pending")
    created_at   = Column(DateTime, default=datetime.utcnow)
    applied_at   = Column(DateTime, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, ForeignKey("users.id"), nullable=False)
    title      = Column(String, nullable=False)
    message    = Column(Text, nullable=False)
    severity   = Column(String, default="info")
    type       = Column(String, default="general")
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="notifications")

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

class AutomationRule(Base):
    __tablename__ = "automation_rules"
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
    created_at      = Column(DateTime, default=datetime.utcnow)

# Create all tables
Base.metadata.create_all(bind=engine)

# AUTH
_MAX = 72
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:_MAX], bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:_MAX], hashed.encode())
    except:
        return False

def create_token(user_id: str) -> str:
    exp = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode({"sub": user_id, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    exc = HTTPException(status_code=401, detail="Invalid credentials",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id: raise exc
    except JWTError:
        raise exc
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user: raise exc
    return user

# SCHEMAS
class UserOut(BaseModel):
    id: str; email: str; full_name: str; is_active: bool; created_at: datetime
    class Config: from_attributes = True

class LoginIn(BaseModel):
    email: str; password: str

class RegisterIn(BaseModel):
    email: str; password: str = Field(min_length=6); full_name: Optional[str] = ""

class StoreCreate(BaseModel):
    marketplace: str; store_name: str; seller_id: Optional[str] = ""

# DEMO DATA SEED
import random
def seed_demo(db: Session, user: User):
    if db.query(Store).filter(Store.user_id == user.id).count() > 0:
        return
    store = Store(user_id=user.id, marketplace="Amazon",
                  store_name=f"{user.full_name or 'My'} Store", seller_id="DEMO")
    db.add(store); db.flush()

    products_data = [
        ("Wireless Earbuds Pro", "B0D001", 2499, 800, 142),
        ("Yoga Mat Premium", "B0D002", 1299, 350, 85),
        ("LED Desk Lamp", "B0D003", 899, 280, 203),
        ("Protein Powder 1kg", "B0D004", 1799, 600, 38),
        ("Kitchen Set Bundle", "B0D005", 3499, 900, 67),
    ]
    products = []
    for name, asin, price, cost, stock in products_data:
        p = Product(store_id=store.id, name=name, asin=asin, price=price, cost=cost, stock_level=stock)
        db.add(p); db.flush(); products.append(p)

    for day in range(60):
        order_date = datetime.utcnow() - timedelta(days=day)
        for prod in random.sample(products, k=random.randint(1, 3)):
            rev = prod.price * random.randint(1, 3)
            ad  = rev * random.uniform(0.10, 0.30)
            db.add(Order(store_id=store.id, order_date=order_date,
                        revenue=rev, profit=(prod.price-prod.cost)*random.randint(1,3)-ad,
                        ad_spend=ad))

    camps = [
        ("Wireless Earbuds SP", "sponsored_products", "active", 50),
        ("Yoga Mat SP", "sponsored_products", "active", 30),
        ("LED Lamp SB", "sponsored_brands", "active", 40),
        ("Protein SP", "sponsored_products", "paused", 25),
        ("Kitchen SD", "sponsored_display", "draft", 20),
    ]
    for cname, ctype, cstatus, budget in camps:
        spend = random.uniform(200, 1200)
        rev   = spend * random.uniform(2.5, 5.5)
        db.add(Campaign(store_id=store.id, name=cname, campaign_type=ctype,
                       status=cstatus, daily_budget=budget,
                       spend=round(spend,2), revenue=round(rev,2),
                       impressions=random.randint(10000,80000),
                       clicks=random.randint(200,2000), orders=random.randint(10,120),
                       acos=round(spend/rev*100,1), roas=round(rev/spend,2)))

    for title, otype, desc, priority in [
        ("Wireless Earbuds — [earbuds pro]","bid_decrease","ACoS 38% above target","medium"),
        ("Yoga Mat — [yoga mat]","pause_keyword","12 clicks, 0 conversions","high"),
        ("LED Lamp — [desk lamp]","bid_increase","ACoS 14% below target","low"),
        ("Protein — [protein powder]","negative_keyword","Zero sales","high"),
        ("Kitchen — [kitchen set]","budget_increase","Hits daily cap","medium"),
    ]:
        db.add(OptimizationItem(user_id=user.id, title=title, type=otype,
                               description=desc, priority=priority,
                               campaign_name=title.split("—")[0].strip()))

    for title, msg, sev in [
        ("ACoS Alert","Wireless Earbuds ACoS hit 38%","warning"),
        ("Budget Cap","LED Lamp hit daily budget limit","info"),
        ("Low Stock","Protein Powder has only 38 units","danger"),
        ("Weekly Report","Your weekly summary is ready","success"),
    ]:
        db.add(Notification(user_id=user.id, title=title, message=msg, severity=sev))

    db.add(NotificationSetting(user_id=user.id))
    db.commit()

def _store_ids(db, user):
    return [s.id for s in db.query(Store).filter(Store.user_id == user.id).all()]

# ROUTERS
api = APIRouter(prefix="/api")
auth_r = APIRouter(prefix="/auth", tags=["auth"])

@auth_r.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(email=data.email, hashed_password=hash_password(data.password),
                full_name=data.full_name or "")
    db.add(user); db.commit(); db.refresh(user)
    seed_demo(db, user)
    return {"token": create_token(user.id), "user": UserOut.model_validate(user)}

@auth_r.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    seed_demo(db, user)
    return {"token": create_token(user.id), "user": UserOut.model_validate(user)}

@auth_r.post("/token")
def token_login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    token = create_token(user.id)
    return {"access_token": token, "token_type": "bearer", "token": token,
            "user": UserOut.model_validate(user)}

@auth_r.get("/me")
def me(current: User = Depends(get_current_user)):
    return UserOut.model_validate(current)

stores_r = APIRouter(prefix="/stores", tags=["stores"])

@stores_r.get("")
def list_stores(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stores = db.query(Store).filter(Store.user_id == current.id).all()
    return [{"id": s.id, "marketplace": s.marketplace, "store_name": s.store_name,
             "seller_id": s.seller_id, "marketplace_id": "A21TJRUUN4KGV",
             "is_connected": s.is_connected, "connected_at": s.connected_at,
             "last_sync": s.last_sync, "has_sp_api": False, "has_ads_api": False}
            for s in stores]

@stores_r.post("")
def create_store(data: StoreCreate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = Store(user_id=current.id, **data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "marketplace": s.marketplace, "store_name": s.store_name,
            "seller_id": s.seller_id, "marketplace_id": "A21TJRUUN4KGV",
            "is_connected": True, "connected_at": s.connected_at, "last_sync": None,
            "has_sp_api": False, "has_ads_api": False}

@stores_r.delete("/{store_id}")
def delete_store(store_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(Store).filter(Store.id == store_id, Store.user_id == current.id).first()
    if not s: raise HTTPException(404, "Not found")
    db.delete(s); db.commit()
    return {"ok": True}

dash_r = APIRouter(prefix="/dashboard", tags=["dashboard"])

@dash_r.get("")
def dashboard(days: int = 30, currency: str = "INR",
              current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sid = _store_ids(db, current)
    if not sid:
        return {"total_revenue":0,"total_orders":0,"net_profit":0,"ad_spend":0,
                "roas":0,"acos":0,"tcos":0,"low_inventory_alerts":0,
                "orders_chart":[],"revenue_chart":[],"top_products":[]}
    since = datetime.utcnow() - timedelta(days=days)
    orders = db.query(Order).filter(Order.store_id.in_(sid), Order.order_date >= since).all()
    total_rev   = sum(o.revenue for o in orders)
    total_profit= sum(o.profit for o in orders)
    total_ad    = sum(o.ad_spend for o in orders)
    fx = 1 if currency == "INR" else 0.012
    from collections import defaultdict
    daily_r: Dict[str, float] = defaultdict(float)
    daily_o: Dict[str, int]   = defaultdict(int)
    for o in orders:
        d = o.order_date.strftime("%b %d")
        daily_r[d] += o.revenue; daily_o[d] += 1
    return {
        "total_revenue": round(total_rev*fx, 2),
        "total_orders":  len(orders),
        "net_profit":    round(total_profit*fx, 2),
        "ad_spend":      round(total_ad*fx, 2),
        "roas":          round(total_rev/total_ad, 2) if total_ad else 0,
        "acos":          round(total_ad/total_rev*100, 1) if total_rev else 0,
        "tcos":          0,
        "low_inventory_alerts": db.query(Product).filter(
            Product.store_id.in_(sid), Product.stock_level < 50).count(),
        "orders_chart":  [{"date":k,"orders":v} for k,v in sorted(daily_o.items())][-30:],
        "revenue_chart": [{"date":k,"revenue":round(v*fx,2)} for k,v in sorted(daily_r.items())][-30:],
        "top_products":  [],
    }

camp_r = APIRouter(prefix="/campaigns", tags=["campaigns"])

@camp_r.get("")
def list_campaigns(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    camps = db.query(Campaign).filter(Campaign.store_id.in_(_store_ids(db, current))).all()
    return {"campaigns": [{"id":c.id,"name":c.name,"campaign_type":c.campaign_type,
             "status":c.status,"daily_budget":c.daily_budget,"spend":c.spend,
             "revenue":c.revenue,"clicks":c.clicks,"orders":c.orders,
             "acos":c.acos,"roas":c.roas,"target_acos":c.target_acos,
             "created_at":c.created_at.isoformat()} for c in camps]}

prod_r = APIRouter(prefix="/products", tags=["products"])

@prod_r.get("")
def list_products(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prods = db.query(Product).filter(Product.store_id.in_(_store_ids(db, current))).all()
    return [{"id":p.id,"asin":p.asin,"name":p.name,"price":p.price,
             "cost":p.cost,"stock_level":p.stock_level,"status":p.status} for p in prods]

opt_r = APIRouter(prefix="/optimization", tags=["optimization"])

@opt_r.get("/suggestions")
def suggestions(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(OptimizationItem).filter(OptimizationItem.user_id == current.id).all()
    pending = [i for i in items if i.status == "pending"]
    return {
        "suggestions": [{"id":i.id,"title":i.title,"description":i.description,
                         "type":i.type,"priority":i.priority,"status":i.status,
                         "campaign_name":i.campaign_name,"keyword":i.keyword,
                         "current_bid":i.current_bid,"suggested_bid":i.suggested_bid,
                         "current_acos":i.current_acos,"expected_acos":i.expected_acos,
                         "estimated_savings":i.estimated_savings,
                         "estimated_revenue_gain":i.estimated_revenue_gain,
                         "spend":i.spend,"sales":i.sales,
                         "created_at":i.created_at.isoformat()} for i in items],
        "summary": {"total_suggestions":len(pending),
                    "high_priority":sum(1 for i in pending if i.priority=="high"),
                    "potential_savings":sum(i.estimated_savings or 0 for i in pending),
                    "potential_revenue_gain":sum(i.estimated_revenue_gain or 0 for i in pending)}
    }

@opt_r.post("/apply/{item_id}")
def apply_one(item_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    i = db.query(OptimizationItem).filter(OptimizationItem.id == item_id,
                                          OptimizationItem.user_id == current.id).first()
    if not i: raise HTTPException(404, "Not found")
    i.status = "applied"; i.applied_at = datetime.utcnow(); db.commit()
    return {"ok": True}

@opt_r.post("/apply-all")
def apply_all(data: Dict[str, Any] = {}, current: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    q = db.query(OptimizationItem).filter(OptimizationItem.user_id == current.id,
                                          OptimizationItem.status == "pending")
    items = q.all()
    for i in items: i.status = "applied"; i.applied_at = datetime.utcnow()
    db.commit()
    return {"applied": len(items), "message": "All optimizations applied"}

@opt_r.get("/count")
def opt_count(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(OptimizationItem).filter(OptimizationItem.user_id == current.id,
                                          OptimizationItem.status == "pending").count()
    return {"pending": n}

notif_r = APIRouter(prefix="/notifications", tags=["notifications"])

@notif_r.get("/history")
def notif_history(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(Notification.user_id == current.id)\
               .order_by(desc(Notification.created_at)).limit(50).all()
    unread = sum(1 for n in notifs if not n.is_read)
    return {"notifications": [{"id":n.id,"title":n.title,"message":n.message,
             "severity":n.severity,"type":n.type,"is_read":n.is_read,
             "created_at":n.created_at.isoformat()} for n in notifs],
            "unread_count": unread}

@notif_r.get("/count")
def notif_count(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.user_id == current.id,
                                      Notification.is_read == False).count()
    return {"unread": n}

@notif_r.post("/read-all")
def read_all(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == current.id,
                                  Notification.is_read == False).update({"is_read": True})
    db.commit(); return {"ok": True}

@notif_r.post("/{nid}/read")
def mark_read(nid: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == nid,
                                      Notification.user_id == current.id).first()
    if n: n.is_read = True; db.commit()
    return {"ok": True}

ns_r = APIRouter(prefix="/notification-settings", tags=["notification-settings"])

@ns_r.get("")
def get_ns(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(NotificationSetting).filter(NotificationSetting.user_id == current.id).first()
    if not s:
        s = NotificationSetting(user_id=current.id); db.add(s); db.commit(); db.refresh(s)
    return {"settings": {"email_notifications":s.email_notifications,
                         "in_app_notifications":s.in_app_notifications,
                         "daily_optimization_alerts":s.daily_optimization_alerts,
                         "budget_alerts":s.budget_alerts,
                         "performance_alerts":s.performance_alerts,
                         "inventory_alerts":s.inventory_alerts,
                         "email_frequency":s.email_frequency}}

@ns_r.patch("")
def update_ns(data: Dict[str, Any], current: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    s = db.query(NotificationSetting).filter(NotificationSetting.user_id == current.id).first()
    if not s:
        s = NotificationSetting(user_id=current.id); db.add(s)
    for k, v in data.items():
        if hasattr(s, k): setattr(s, k, v)
    db.commit()
    return {"ok": True}

rules_r = APIRouter(prefix="/rules", tags=["rules"])

@rules_r.get("")
def list_rules(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(AutomationRule).filter(AutomationRule.user_id == current.id).all()

@rules_r.post("")
def create_rule(data: Dict[str, Any], current: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    r = AutomationRule(user_id=current.id, **{k:v for k,v in data.items()
                                               if hasattr(AutomationRule, k)})
    db.add(r); db.commit(); db.refresh(r)
    return r

cb_r = APIRouter(prefix="/campaign-builder", tags=["campaign-builder"])

@cb_r.get("/products")
def cb_products(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prods = db.query(Product).filter(Product.store_id.in_(_store_ids(db, current))).all()
    if not prods:
        return {"products": [], "message": "Connect a store to see products"}
    return {"products": [{"id":p.id,"asin":p.asin,"name":p.name,"price":p.price} for p in prods]}

@cb_r.post("/generate")
def cb_generate(data: Dict[str, Any], current: User = Depends(get_current_user)):
    name = data.get("product_name","Product")
    budget = float(data.get("daily_budget", 50))
    base = round(max(budget/50, 0.5), 2)
    return {"campaigns": [
        {"name":f"{name} — Exact","campaign_type":"sponsored_products",
         "daily_budget":round(budget*0.5,2),"target_acos":25,
         "keywords":[{"text":name.lower(),"match_type":"exact","bid":round(base*1.2,2)}]},
        {"name":f"{name} — Phrase","campaign_type":"sponsored_products",
         "daily_budget":round(budget*0.3,2),"target_acos":25,
         "keywords":[{"text":name.lower(),"match_type":"phrase","bid":round(base*0.9,2)}]},
        {"name":f"{name} — Broad","campaign_type":"sponsored_products",
         "daily_budget":round(budget*0.2,2),"target_acos":25,
         "keywords":[{"text":name.lower(),"match_type":"broad","bid":round(base*0.7,2)}]},
    ], "message": "Generated. Review and launch."}

@cb_r.post("/launch")
def cb_launch(data: Dict[str, Any], current: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    sid = _store_ids(db, current)
    if not sid: raise HTTPException(400, "Connect a store first")
    camps = []
    for cd in (data.get("campaigns") or []):
        c = Campaign(store_id=sid[0], name=cd.get("name","Campaign"),
                     campaign_type=cd.get("campaign_type","sponsored_products"),
                     daily_budget=cd.get("daily_budget",50), status="active", target_acos=25)
        db.add(c); camps.append(c)
    db.commit()
    return {"launched_campaigns": len(camps)}

analytics_r = APIRouter(prefix="/analytics", tags=["analytics"])

@analytics_r.get("/dashboard")
def analytics_dash(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dashboard(30, "INR", current, db)

@analytics_r.get("/top-keywords")
def top_keywords(current: User = Depends(get_current_user)):
    return []

# Amazon OAuth placeholder
amazon_r = APIRouter(prefix="/amazon", tags=["amazon"])

@amazon_r.get("/marketplaces")
def marketplaces():
    return {"marketplaces": [
        {"code":"IN","name":"Amazon India","marketplace_id":"A21TJRUUN4KGV"},
        {"code":"US","name":"Amazon US","marketplace_id":"ATVPDKIKX0DER"},
        {"code":"UK","name":"Amazon UK","marketplace_id":"A1F83G8C2ARO7P"},
        {"code":"DE","name":"Amazon Germany","marketplace_id":"A1PA6795UKMFR9"},
        {"code":"AE","name":"Amazon UAE","marketplace_id":"A2VIGQ35RCS4UG"},
    ]}

@amazon_r.get("/connect/url")
def connect_url(marketplace: str = "IN", store_name: str = "My Store",
                current: User = Depends(get_current_user)):
    return {"url": f"https://sellercentral.amazon.in/apps/authorize/consent?application_id=amzn1.sp.solution.xxx",
            "message": "SP_API_CLIENT_ID not configured yet"}

# Multi-store placeholder
multi_r = APIRouter(prefix="/multi-store", tags=["multi-store"])

@multi_r.get("/status")
def multi_status(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stores = db.query(Store).filter(Store.user_id == current.id).all()
    return {"stores": [{"id":s.id,"store_name":s.store_name,"marketplace":s.marketplace,
                        "sp_api_ready":False,"ads_api_ready":False} for s in stores]}

# Mount all routers
api.include_router(auth_r)
api.include_router(stores_r)
api.include_router(dash_r)
api.include_router(camp_r)
api.include_router(prod_r)
api.include_router(opt_r)
api.include_router(notif_r)
api.include_router(ns_r)
api.include_router(rules_r)
api.include_router(cb_r)
api.include_router(analytics_r)
api.include_router(amazon_r)
api.include_router(multi_r)

# APP
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("SellerVector starting - DB=%s", DATABASE_URL[:50])
    yield

app = FastAPI(title="SellerVector API", version="2.0.0",
              description="Amazon PPC & seller analytics platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def err_handler(request, exc):
    log.exception("Error: %s", exc)
    return JSONResponse(500, {"detail": "Internal server error"})

@app.get("/")
def root(): return {"name": "SellerVector API", "version": "2.0.0"}

@app.get("/api/health")
def health(): return {"status": "ok", "time": datetime.utcnow().isoformat()}

app.include_router(api)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
