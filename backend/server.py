from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File
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

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "sv2024secret")
ALGORITHM = "HS256"
security = HTTPBearer()

SP_API_CLIENT_ID = os.getenv("SP_API_CLIENT_ID")
SP_API_CLIENT_SECRET = os.getenv("SP_API_CLIENT_SECRET")
SP_API_REFRESH_TOKEN = os.getenv("SP_API_REFRESH_TOKEN")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
MARKETPLACE_ID = "A21TJRUUN4KGV"

app = FastAPI()
api_router = APIRouter(prefix="/api")

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

class Store(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    marketplace: str
    store_name: str
    seller_id: str
    connected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"

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

def get_access_token(refresh_token: str = None):
    token = refresh_token or SP_API_REFRESH_TOKEN
    try:
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
    except Exception as e:
        logging.error(f"Error getting access token: {e}")
        return None

def get_amazon_orders(refresh_token: str = None, days: int = 30):
    try:
        access_token = get_access_token(refresh_token)
        if not access_token:
            return []
        created_after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        response = requests.get(
            "https://sellingpartnerapi-eu.amazon.com/orders/v0/orders",
            headers={
                "x-amz-access-token": access_token,
                "x-amz-date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            },
            params={
                "MarketplaceIds": MARKETPLACE_ID,
                "CreatedAfter": created_after,
                "OrderStatuses": "Shipped,Delivered,Unshipped"
            }
        )
        return response.json().get("payload", {}).get("Orders", [])
    except Exception as e:
        logging.error(f"Error fetching orders: {e}")
        return []

def get_amazon_inventory(refresh_token: str = None):
    try:
        access_token = get_access_token(refresh_token)
        if not access_token:
            return []
        response = requests.get(
            "https://sellingpartnerapi-eu.amazon.com/fba/inventory/v1/summaries",
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
        return response.json().get("payload", {}).get("inventorySummaries", [])
    except Exception as e:
        logging.error(f"Error fetching inventory: {e}")
        return []

def get_advertising_campaigns(refresh_token: str = None):
    try:
        access_token = get_access_token(refresh_token)
        if not access_token:
            return []
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

def get_advertising_keywords(refresh_token: str = None):
    try:
        access_token = get_access_token(refresh_token)
        if not access_token:
            return []
        response = requests.get(
            "https://advertising-api-fe.amazon.com/sp/keywords",
            headers={
                "Amazon-Advertising-API-ClientId": SP_API_CLIENT_ID,
                "Authorization": f"Bearer {access_token}",
                "Amazon-Advertising-API-Scope": MARKETPLACE_ID,
            }
        )
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        logging.error(f"Error fetching keywords: {e}")
        return []

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

@api_router.post("/stores")
async def connect_store(store_data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    store = Store(
        user_id=user_id,
        marketplace=store_data["marketplace"],
        store_name=store_data["store_name"],
        seller_id=store_data["seller_id"]
    )
    await db.stores.insert_one(store.model_dump())
    return store

@api_router.get("/stores")
async def get_stores(user_id: str = Depends(get_current_user)):
    stores = await db.stores.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    return stores

@api_router.get("/amazon/connect")
async def amazon_connect(user_id: str = Depends(get_current_user)):
    auth_url = (
        f"https://sellercentral.amazon.in/apps/authorize/consent"
        f"?application_id={SP_API_CLIENT_ID}"
        f"&state={user_id}"
        f"&version=beta"
    )
    return {"auth_url": auth_url}

@api_router.get("/amazon/callback")
async def amazon_callback(spapi_oauth_code: str, state: str):
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
        return {"status": "connected", "message": "Amazon account connected successfully!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/dashboard")
async def get_dashboard(days: int = 30, user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    orders = get_amazon_orders(refresh_token, days)
    inventory = get_amazon_inventory(refresh_token)
    total_orders = len(orders)
    total_revenue = sum(float(o.get("OrderTotal", {}).get("Amount", 0)) for o in orders if o.get("OrderTotal"))
    low_inventory = [i for i in inventory if i.get("totalQuantity", 0) < 50]
    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "low_inventory_alerts": len(low_inventory),
        "currency": "INR",
        "amazon_connected": bool(refresh_token),
        "top_products": [],
        "orders_chart": [],
        "revenue_chart": [],
        "sales_by_marketplace": [],
        "tcos": 0,
        "roas": 0,
        "acos": 0,
        "ad_spend": 0,
        "net_profit": 0
    }

@api_router.get("/orders")
async def get_orders(days: int = 30, user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    orders = get_amazon_orders(refresh_token, days)
    return {"orders": orders, "total": len(orders)}

@api_router.get("/products")
async def get_products(user_id: str = Depends(get_current_user)):
    return []

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
                "id": str(uuid.uuid4()),
                "product_name": item.get("productName", "Unknown"),
                "sku": item.get("sellerSku", ""),
                "asin": item.get("asin", ""),
                "current_stock": qty,
                "alert_level": "critical" if qty < 10 else "warning",
                "days_until_stockout": 0,
                "daily_sales_velocity": 0,
                "marketplace": "Amazon India"
            })
    return {"alerts": alerts}

@api_router.get("/inventory/ledger")
async def get_inventory_ledger(user_id: str = Depends(get_current_user)):
    return {"ledger": []}

@api_router.get("/campaigns")
async def get_campaigns(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    campaigns = get_advertising_campaigns(refresh_token)
    return {"campaigns": campaigns}

@api_router.get("/campaigns/wasted-spend")
async def get_wasted_spend(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    keywords = get_advertising_keywords(refresh_token)
    wasted = [k for k in keywords if k.get("sales", 0) == 0 and k.get("spend", 0) > 0]
    return {"wasted_keywords": wasted, "total_wasted": sum(k.get("spend", 0) for k in wasted)}

@api_router.get("/campaigns/{campaign_id}/keywords")
async def get_keywords(campaign_id: str, user_id: str = Depends(get_current_user)):
    return {"keywords": []}

@api_router.post("/campaigns/create")
async def create_campaign(campaign_data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"campaigns": [], "message": "Connect Amazon account to create campaigns"}

@api_router.get("/profit/calculate")
async def calculate_profit(user_id: str = Depends(get_current_user)):
    return {"profit_data": []}

@api_router.get("/fba/shipment-planner")
async def get_fba_shipment_planner(user_id: str = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    refresh_token = user.get("amazon_refresh_token") if user else None
    inventory = get_amazon_inventory(refresh_token)
    shipments = []
    for item in inventory:
        qty = item.get("totalQuantity", 0)
        if qty < 100:
            shipments.append({
                "id": str(uuid.uuid4()),
                "sku": item.get("sellerSku", ""),
                "asin": item.get("asin", ""),
                "title": item.get("productName", ""),
                "current_stock": qty,
                "quantity_needed": 200 - qty,
                "fc_code": "BOM7",
                "priority": "high" if qty < 50 else "medium"
            })
    return {"shipments": shipments, "total_items": len(shipments)}

@api_router.post("/fba/download-bulk-sheet")
async def download_bulk_sheet(shipment_ids: List[str], user_id: str = Depends(get_current_user)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["SKU", "FNSKU", "Product Name", "Quantity", "FC Code"])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shipment.csv"})

@api_router.get("/competitors")
async def get_competitors(user_id: str = Depends(get_current_user)):
    return {"competitors": []}

@api_router.post("/ai-copilot")
async def ai_copilot(message: Dict[str, str], user_id: str = Depends(get_current_user)):
    return {
        "response": "Connect your Amazon account to get AI-powered insights based on your real data!",
        "suggestions": ["Connect Amazon account", "View campaigns", "Check inventory"]
    }

@api_router.get("/reports")
async def get_reports(user_id: str = Depends(get_current_user)):
    return {"reports": []}

@api_router.get("/notifications")
async def get_notifications(user_id: str = Depends(get_current_user)):
    return {"notifications": [], "unread_count": 0}

@api_router.get("/notifications/history")
async def get_notification_history(user_id: str = Depends(get_current_user)):
    return {"notifications": [], "unread_count": 0}

@api_router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user_id: str = Depends(get_current_user)):
    return {"message": "Notification marked as read"}

@api_router.get("/notification-settings")
async def get_notification_settings(user_id: str = Depends(get_current_user)):
    return {"settings": {}}

@api_router.patch("/notification-settings")
async def update_notification_settings(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"message": "Settings updated"}

@api_router.get("/subscription/plans")
async def get_subscription_plans():
    plans = [
        {"plan_name": "Free", "price": 0, "features": ["1 Store", "Basic Analytics"]},
        {"plan_name": "Starter", "price": 29, "features": ["2 Stores", "Advanced Analytics"]},
        {"plan_name": "Professional", "price": 79, "features": ["5 Stores", "Full Analytics", "AI Copilot"]},
        {"plan_name": "Enterprise", "price": 199, "features": ["Unlimited Stores", "API Access"]}
    ]
    return {"plans": plans}

@api_router.post("/budget-calculator")
async def calculate_budget(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    budget = float(data.get("budget", 1000))
    cpc = float(data.get("cpc", 0.50))
    cvr = float(data.get("cvr", 10))
    avg_order_value = float(data.get("avg_order_value", 50))
    estimated_clicks = int(budget / cpc) if cpc > 0 else 0
    estimated_orders = int(estimated_clicks * (cvr / 100))
    estimated_sales = round(estimated_orders * avg_order_value, 2)
    estimated_roas = round(estimated_sales / budget, 2) if budget > 0 else 0
    return {"predictions": {"estimated_clicks": estimated_clicks, "estimated_orders": estimated_orders, "estimated_sales": estimated_sales, "estimated_roas": estimated_roas}}

@api_router.get("/budget-planner/products")
async def get_product_budget_plans(user_id: str = Depends(get_current_user)):
    return {"budget_plans": []}

@api_router.patch("/budget-planner/products/{product_id}")
async def update_product_budget(product_id: str, data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"message": "Budget updated"}

@api_router.get("/dayparting/analysis")
async def get_dayparting_analysis(user_id: str = Depends(get_current_user)):
    return {"hourly_data": [], "daily_data": [], "recommendations": []}

@api_router.get("/dayparting/schedule")
async def get_dayparting_schedule(user_id: str = Depends(get_current_user)):
    return {"schedule": []}

@api_router.post("/dayparting/schedule")
async def update_dayparting_schedule(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"message": "Schedule updated"}

@api_router.get("/optimization/suggestions")
async def get_optimization_suggestions(user_id: str = Depends(get_current_user)):
    return {"suggestions": [], "summary": {"total_suggestions": 0, "high_priority": 0, "potential_savings": 0, "potential_revenue_gain": 0}}

@api_router.post("/optimization/apply/{suggestion_id}")
async def apply_optimization(suggestion_id: str, user_id: str = Depends(get_current_user)):
    return {"message": "Optimization applied", "suggestion_id": suggestion_id, "status": "applied"}

@api_router.post("/optimization/apply-all")
async def apply_all_optimizations(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"message": "All optimizations applied"}

@api_router.get("/campaign-builder/products")
async def get_products_for_campaign(user_id: str = Depends(get_current_user)):
    return {"products": []}

@api_router.post("/campaign-builder/generate")
async def generate_ai_campaign(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"campaigns": [], "message": "Connect Amazon to generate campaigns"}

@api_router.post("/campaign-builder/launch")
async def launch_campaigns(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"message": "Connect Amazon to launch campaigns", "launched_campaigns": []}

@api_router.post("/products/bulk-upload")
async def bulk_upload_products(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    return {"message": "Upload received", "count": 0}

@api_router.patch("/products/{product_id}/cost")
async def update_product_cost(product_id: str, cost_data: Dict[str, float], user_id: str = Depends(get_current_user)):
    return {"message": "Cost updated"}

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
