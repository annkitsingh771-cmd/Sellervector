from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import requests
import io
import csv
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "sv2024secret")
ALGORITHM = "HS256"
security = HTTPBearer()

# Amazon API Credentials
SP_API_CLIENT_ID = os.getenv("SP_API_CLIENT_ID")
SP_API_CLIENT_SECRET = os.getenv("SP_API_CLIENT_SECRET")
SP_API_REFRESH_TOKEN = os.getenv("SP_API_REFRESH_TOKEN")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
MARKETPLACE_ID = "A21TJRUUN4KGV"  # Amazon India

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ============= Models =============
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    token: str
    user: Dict[str, Any]

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: str
    subscription_plan: str = "free"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ============= Helper Functions =============
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_token(user_id: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode({"user_id": user_id, "exp": expiration}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============= Amazon API Functions =============
def get_access_token(refresh_token: str = None):
    """Get Amazon access token"""
    token = refresh_token or SP_API_REFRESH_TOKEN
    response = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": token,
            "client_id": SP_API_CLIENT_ID,
            "client_secret": SP_API_CLIENT_SECRET,
        }
    )
    return response.json().get("access_token")

def get_amazon_orders(refresh_token: str = None, days: int = 30):
    """Get real orders from Amazon SP-API"""
    try:
        access_token = get_access_token(refresh_token)
        created_after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        response = requests.get(
            "https://sellingpartnerapi-fe.amazon.com/orders/v0/orders",
            headers={
                "x-amz-access-token": access_token,
                "x-amz-date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            },
            params={
                "MarketplaceIds": MARKETPLACE_ID,
                "CreatedAfter": created_after,
                "OrderStatuses": "Shipped,Delivered"
            }
        )
        data = response.json()
        orders = data.get("payload", {}).get("Orders", [])
        return orders
    except Exception as e:
        logging.error(f"Error fetching orders: {e}")
        return []

def get_amazon_inventory(refresh_token: str = None):
    """Get real inventory from Amazon SP-API"""
    try:
        access_token = get_access_token(refresh_token)
        response = requests.get(
            "https://sellingpartnerapi-fe.amazon.com/fba/inventory/v1/summaries",
            headers={
                "x-amz-access-token": access_token,
                "x-amz-date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            },
            params={
                "details": True,
                "marketplaceIds": MARKETPLACE_ID,
                "granularityType": "Marketplace",
                "granularityId": MARKETPLACE_ID
            }
        )
        data = response.json()
        return data.get("payload", {}).get("inventorySummaries", [])
    except Exception as e:
        logging.error(f"Error fetching inventory: {e}")
        return []

def get_advertising_campaigns(refresh_token: str = None):
    """Get real campaigns from Amazon Advertising API"""
    try:
        access_token = get_access_token(refresh_token)
        response = requests.get(
            "https://advertising-api-fe.amazon.com/sp/campaigns",
            headers={
                "Amazon-Advertising-API-ClientId": SP_API_CLIENT_ID,
                "Authorization": f"Bearer {access_token}",
                "Amazon-Advertising-API-Scope": MARKETPLACE_ID,
            }
        )
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        logging.error(f"Error fetching campaigns: {e}")
        return []

# ============= Auth Routes =============
@api_router.get("/")
async def root():
    return {"message": "SellerVector API", "status": "running"}

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=user_data.email, full_name=user_data.full_name)
    user_dict = user.model_dump()
    user_dict["password_hash"] = hash_password(user_data.password)
    await db.users.insert_one(user_dict)
    token = create_token(user.id)
    return TokenResponse(
        token=token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name, "subscription_plan": user.subscription_plan}
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"])
    return TokenResponse(
        token=token,
        user={"id": user["id"], "email": user["email"], "full_name": user["full_name"], "subscription_plan": user.get("subscription_plan", "free")}
    )

# ============= Amazon OAuth =============
@api_router.get("/amazon/connect")
async def amazon_connect(user_id: str = Depends(get_current_user)):
    """Generate Amazon authorization URL"""
    auth_url = (
        f"https://sellercentral.amazon.in/apps/authorize/consent"
        f"?application_id={SP_API_CLIENT_ID}"
        f"&state={user_id}"
        f"&version=beta"
    )
    return {"auth_url": auth_url}

@api_router.get("/amazon/callback")
async def amazon_callback(spapi_oauth_code: str, state: str):
    """Handle Amazon OAuth callback"""
    try:
        response = requests.post(
            "https://api.amazon.com/auth/o2/token",
            data={
                "grant_type": "authorization_code",
                "code": spapi_oauth_code,
                "client_id": SP_API_CLIENT_ID,
                "client_secret": SP_API_CLIENT_SECRET,
            }
        )
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")
        await db.users.update_one(
            {"id": state},
            {"$set": {"amazon_refresh_token": refresh_token, "amazon_connected": True}}
        )
        return {"status": "connected", "message": "Amazon account connected!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============= Dashboard =============
@api_router.get("/dashboard")
async def get_dashboard(days: int = 30, user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None

    orders = get_amazon_orders(refresh_token, days)
    inventory = get_amazon_inventory(refresh_token)

    total_orders = len(orders)
    total_revenue = sum(
        float(o.get("OrderTotal", {}).get("Amount", 0))
        for o in orders
    )

    low_inventory = [i for i in inventory if i.get("totalQuantity", 0) < 50]

    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "low_inventory_alerts": len(low_inventory),
        "currency": "INR",
        "amazon_connected": bool(refresh_token)
    }

# ============= Orders =============
@api_router.get("/orders")
async def get_orders(days: int = 30, user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    orders = get_amazon_orders(refresh_token, days)
    return {"orders": orders, "total": len(orders)}

# ============= Inventory =============
@api_router.get("/inventory/alerts")
async def get_inventory_alerts(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    inventory = get_amazon_inventory(refresh_token)
    
    alerts = []
    for item in inventory:
        qty = item.get("totalQuantity", 0)
        if qty < 50:
            alerts.append({
                "product_name": item.get("productName", "Unknown"),
                "sku": item.get("sellerSku", ""),
                "asin": item.get("asin", ""),
                "current_stock": qty,
                "alert_level": "critical" if qty < 10 else "warning"
            })
    return {"alerts": alerts}

# ============= Campaigns =============
@api_router.get("/campaigns")
async def get_campaigns(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    campaigns = get_advertising_campaigns(refresh_token)
    return {"campaigns": campaigns}

# ============= Subscription Plans =============
@api_router.get("/subscription/plans")
async def get_subscription_plans():
    plans = [
        {"plan_name": "Free", "price": 0, "features": ["1 Store", "Basic Analytics", "10 Products"]},
        {"plan_name": "Starter", "price": 29, "features": ["2 Stores", "Advanced Analytics", "50 Products"]},
        {"plan_name": "Professional", "price": 79, "features": ["5 Stores", "Full Analytics", "Unlimited Products", "AI Copilot"]},
        {"plan_name": "Enterprise", "price": 199, "features": ["Unlimited Stores", "Custom Reports", "API Access", "Dedicated Support"]}
    ]
    return {"plans": plans}

# ============= Notifications =============
@api_router.get("/notifications")
async def get_notifications(user_id: str = Depends(get_current_user)):
    return {"notifications": [], "unread_count": 0}

app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("SellerVector API started!")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
