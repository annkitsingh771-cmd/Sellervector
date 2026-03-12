from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
import random
from faker import Faker

fake = Faker()

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
security = HTTPBearer()

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

class DashboardMetrics(BaseModel):
    total_revenue: float
    total_orders: int
    net_profit: float
    ad_spend: float
    roas: float
    acos: float
    top_products: List[Dict[str, Any]]
    low_inventory_alerts: int
    sales_by_marketplace: List[Dict[str, Any]]
    orders_chart: List[Dict[str, Any]]
    revenue_chart: List[Dict[str, Any]]

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    order_number: str
    product_name: str
    quantity: int
    revenue: float
    marketplace: str
    order_date: str
    status: str

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    name: str
    sku: str
    price: float
    stock_level: int
    revenue: float
    orders: int
    conversion_rate: float
    ad_spend: float
    profit: float
    marketplace: str

class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    product_id: str
    campaign_name: str
    campaign_type: str
    budget: float
    status: str
    ad_spend: float
    ad_sales: float
    acos: float
    roas: float
    impressions: int
    clicks: int
    orders: int
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CampaignCreate(BaseModel):
    product_id: str
    product_name: str
    auto_generate: bool = True

class Keyword(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    keyword: str
    match_type: str
    bid: float
    impressions: int
    clicks: int
    spend: float
    sales: float
    acos: float
    orders: int
    status: str

class InventoryAlert(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: str
    current_stock: int
    daily_sales_velocity: float
    days_until_stockout: int
    alert_level: str
    marketplace: str

class Competitor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    competitor_name: str
    competitor_price: float
    your_price: float
    price_difference: float
    review_count: int
    rating: float
    marketplace: str

class AIMessage(BaseModel):
    message: str

class AIResponse(BaseModel):
    response: str
    suggestions: List[str]

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

# Mock data generators
def generate_mock_orders(store_id: str, days: int = 30) -> List[Dict[str, Any]]:
    orders = []
    for i in range(random.randint(50, 150)):
        order_date = datetime.now(timezone.utc) - timedelta(days=random.randint(0, days))
        orders.append({
            "id": str(uuid.uuid4()),
            "store_id": store_id,
            "order_number": f"ORD-{random.randint(10000, 99999)}",
            "product_name": random.choice(["Wireless Headphones", "Running Shoes", "Smartwatch", "Yoga Mat", "Water Bottle", "Laptop Stand", "Phone Case", "Backpack"]),
            "quantity": random.randint(1, 3),
            "revenue": round(random.uniform(20, 200), 2),
            "marketplace": "Amazon",
            "order_date": order_date.isoformat(),
            "status": random.choice(["delivered", "shipped", "processing"])
        })
    return orders

def generate_mock_products(store_id: str) -> List[Dict[str, Any]]:
    products = []
    product_names = ["Wireless Headphones", "Running Shoes", "Smartwatch", "Yoga Mat", "Water Bottle", "Laptop Stand", "Phone Case", "Backpack", "Desk Lamp", "Coffee Maker"]
    for name in product_names:
        revenue = round(random.uniform(500, 5000), 2)
        orders = random.randint(20, 150)
        ad_spend = round(random.uniform(50, 500), 2)
        products.append({
            "id": str(uuid.uuid4()),
            "store_id": store_id,
            "name": name,
            "sku": f"SKU-{random.randint(1000, 9999)}",
            "price": round(random.uniform(15, 150), 2),
            "stock_level": random.randint(5, 500),
            "revenue": revenue,
            "orders": orders,
            "conversion_rate": round(random.uniform(5, 25), 2),
            "ad_spend": ad_spend,
            "profit": round(revenue - ad_spend - (revenue * 0.3), 2),
            "marketplace": "Amazon"
        })
    return products

# ============= Routes =============
@api_router.get("/")
async def root():
    return {"message": "SellerOS API", "status": "running"}

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        full_name=user_data.full_name
    )
    user_dict = user.model_dump()
    user_dict["password_hash"] = hash_password(user_data.password)
    
    await db.users.insert_one(user_dict)
    
    token = create_token(user.id)
    return TokenResponse(
        token=token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name}
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_token(user["id"])
    return TokenResponse(
        token=token,
        user={"id": user["id"], "email": user["email"], "full_name": user["full_name"]}
    )

@api_router.post("/stores", response_model=Store)
async def connect_store(store_data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    store = Store(
        user_id=user_id,
        marketplace=store_data["marketplace"],
        store_name=store_data["store_name"],
        seller_id=store_data["seller_id"]
    )
    await db.stores.insert_one(store.model_dump())
    return store

@api_router.get("/stores", response_model=List[Store])
async def get_stores(user_id: str = Depends(get_current_user)):
    stores = await db.stores.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    return stores

@api_router.get("/dashboard")
async def get_dashboard(store_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    # Mock dashboard data
    orders = generate_mock_orders(store_id or "default")
    products = generate_mock_products(store_id or "default")
    
    total_revenue = sum(o["revenue"] for o in orders)
    total_orders = len(orders)
    ad_spend = sum(p["ad_spend"] for p in products)
    net_profit = sum(p["profit"] for p in products)
    
    # Generate chart data
    orders_chart = []
    revenue_chart = []
    for i in range(30):
        date = (datetime.now(timezone.utc) - timedelta(days=29-i)).strftime("%b %d")
        day_orders = [o for o in orders if (datetime.now(timezone.utc) - datetime.fromisoformat(o["order_date"])).days == (29-i)]
        orders_chart.append({"date": date, "orders": len(day_orders)})
        revenue_chart.append({"date": date, "revenue": sum(o["revenue"] for o in day_orders)})
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "net_profit": round(net_profit, 2),
        "ad_spend": round(ad_spend, 2),
        "roas": round(total_revenue / ad_spend if ad_spend > 0 else 0, 2),
        "acos": round((ad_spend / total_revenue * 100) if total_revenue > 0 else 0, 2),
        "top_products": sorted(products, key=lambda x: x["revenue"], reverse=True)[:5],
        "low_inventory_alerts": len([p for p in products if p["stock_level"] < 50]),
        "sales_by_marketplace": [{"marketplace": "Amazon", "orders": total_orders, "revenue": total_revenue}],
        "orders_chart": orders_chart,
        "revenue_chart": revenue_chart
    }

@api_router.get("/orders")
async def get_orders(store_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    orders = generate_mock_orders(store_id or "default", 60)
    return {"orders": orders, "total": len(orders)}

@api_router.get("/products", response_model=List[Product])
async def get_products(store_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    products = generate_mock_products(store_id or "default")
    return products

@api_router.get("/campaigns")
async def get_campaigns(store_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    campaigns = []
    for i in range(5):
        ad_spend = round(random.uniform(100, 1000), 2)
        ad_sales = round(random.uniform(500, 5000), 2)
        campaigns.append({
            "id": str(uuid.uuid4()),
            "store_id": store_id or "default",
            "product_id": str(uuid.uuid4()),
            "campaign_name": f"Campaign {i+1} - {random.choice(['Auto', 'Manual', 'Product Targeting'])}",
            "campaign_type": random.choice(["auto", "manual", "product_targeting"]),
            "budget": round(random.uniform(500, 2000), 2),
            "status": random.choice(["active", "paused"]),
            "ad_spend": ad_spend,
            "ad_sales": ad_sales,
            "acos": round((ad_spend / ad_sales * 100) if ad_sales > 0 else 0, 2),
            "roas": round(ad_sales / ad_spend if ad_spend > 0 else 0, 2),
            "impressions": random.randint(5000, 50000),
            "clicks": random.randint(100, 2000),
            "orders": random.randint(10, 150),
            "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))).isoformat()
        })
    return {"campaigns": campaigns}

@api_router.post("/campaigns/create")
async def create_campaign(campaign_data: CampaignCreate, user_id: str = Depends(get_current_user)):
    # Auto-generate campaign structure
    campaigns = [
        {
            "id": str(uuid.uuid4()),
            "campaign_name": f"{campaign_data.product_name} - Auto Campaign",
            "campaign_type": "auto",
            "budget": 500,
            "status": "draft",
            "ad_groups": [
                {"name": "Auto Targeting", "bid": 0.75}
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "campaign_name": f"{campaign_data.product_name} - Manual Keywords",
            "campaign_type": "manual",
            "budget": 1000,
            "status": "draft",
            "keywords": [
                {"keyword": f"{campaign_data.product_name.lower()}", "match_type": "exact", "bid": 1.25},
                {"keyword": f"best {campaign_data.product_name.lower()}", "match_type": "phrase", "bid": 1.00},
                {"keyword": f"{campaign_data.product_name.lower()} sale", "match_type": "broad", "bid": 0.85}
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "campaign_name": f"{campaign_data.product_name} - Product Targeting",
            "campaign_type": "product_targeting",
            "budget": 750,
            "status": "draft",
            "targets": ["Competitor ASINs", "Related Categories"]
        }
    ]
    return {"campaigns": campaigns, "message": "Campaigns generated successfully"}

@api_router.get("/campaigns/{campaign_id}/keywords")
async def get_keywords(campaign_id: str, user_id: str = Depends(get_current_user)):
    keywords = []
    for i in range(10):
        spend = round(random.uniform(10, 200), 2)
        sales = round(random.uniform(0, 500), 2)
        keywords.append({
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "keyword": random.choice(["wireless headphones", "bluetooth headphones", "noise cancelling headphones", "best headphones", "gaming headphones", "running headphones", "cheap headphones", "premium headphones", "sport headphones", "workout headphones"]),
            "match_type": random.choice(["exact", "phrase", "broad"]),
            "bid": round(random.uniform(0.5, 2.5), 2),
            "impressions": random.randint(500, 10000),
            "clicks": random.randint(10, 500),
            "spend": spend,
            "sales": sales,
            "acos": round((spend / sales * 100) if sales > 0 else 100, 2),
            "orders": random.randint(0, 20),
            "status": random.choice(["active", "paused"])
        })
    return {"keywords": keywords}

@api_router.get("/campaigns/wasted-spend")
async def get_wasted_spend(user_id: str = Depends(get_current_user)):
    wasted_keywords = []
    for i in range(5):
        spend = round(random.uniform(50, 300), 2)
        wasted_keywords.append({
            "keyword": random.choice(["cheap wireless headphones", "free shipping headphones", "discount bluetooth", "sale electronics", "clearance audio"]),
            "campaign_name": f"Campaign {random.randint(1, 5)}",
            "spend": spend,
            "sales": 0,
            "clicks": random.randint(50, 200),
            "suggestion": "Pause keyword - No sales after $" + str(int(spend)) + " spend"
        })
    return {"wasted_keywords": wasted_keywords, "total_wasted": sum(k["spend"] for k in wasted_keywords)}

@api_router.get("/profit/calculate")
async def calculate_profit(store_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    products = generate_mock_products(store_id or "default")
    profit_data = []
    
    for p in products:
        revenue = p["revenue"]
        referral_fee = revenue * 0.15
        fulfillment_fee = p["orders"] * 3.5
        ad_spend = p["ad_spend"]
        product_cost = revenue * 0.35
        net_profit = revenue - referral_fee - fulfillment_fee - ad_spend - product_cost
        
        profit_data.append({
            "product_name": p["name"],
            "revenue": revenue,
            "referral_fee": round(referral_fee, 2),
            "fulfillment_fee": round(fulfillment_fee, 2),
            "ad_spend": ad_spend,
            "product_cost": round(product_cost, 2),
            "net_profit": round(net_profit, 2),
            "profit_margin": round((net_profit / revenue * 100) if revenue > 0 else 0, 2)
        })
    
    return {"profit_data": profit_data}

@api_router.get("/inventory/alerts")
async def get_inventory_alerts(user_id: str = Depends(get_current_user)):
    alerts = []
    for i in range(5):
        stock = random.randint(5, 50)
        velocity = round(random.uniform(5, 15), 1)
        days_left = int(stock / velocity) if velocity > 0 else 999
        alerts.append({
            "id": str(uuid.uuid4()),
            "product_id": str(uuid.uuid4()),
            "product_name": random.choice(["Wireless Headphones", "Running Shoes", "Smartwatch", "Yoga Mat", "Water Bottle"]),
            "current_stock": stock,
            "daily_sales_velocity": velocity,
            "days_until_stockout": days_left,
            "alert_level": "critical" if days_left < 7 else "warning" if days_left < 14 else "info",
            "marketplace": "Amazon"
        })
    return {"alerts": alerts}

@api_router.get("/competitors")
async def get_competitors(product_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    competitors = []
    your_price = round(random.uniform(25, 50), 2)
    for i in range(5):
        comp_price = round(random.uniform(20, 55), 2)
        competitors.append({
            "id": str(uuid.uuid4()),
            "product_id": product_id or str(uuid.uuid4()),
            "competitor_name": fake.company(),
            "competitor_price": comp_price,
            "your_price": your_price,
            "price_difference": round(comp_price - your_price, 2),
            "review_count": random.randint(50, 5000),
            "rating": round(random.uniform(3.5, 5.0), 1),
            "marketplace": "Amazon"
        })
    return {"competitors": competitors}

@api_router.post("/ai-copilot")
async def ai_copilot(message: AIMessage, user_id: str = Depends(get_current_user)):
    # Mock AI responses
    responses = [
        "Based on your data, I recommend reducing bids for Campaign 4 to improve ACOS by 15%.",
        "Your Wireless Headphones product will run out of stock in 7 days. Consider reducing ad spend or restocking soon.",
        "Campaign 2 has excellent ROAS of 4.5x. I suggest increasing the budget by 25% to maximize profits.",
        "I detected $350 in wasted ad spend on keywords with zero conversions. Would you like me to pause them?",
        "Your profit margin on Running Shoes is only 12%. Consider optimizing product costs or increasing prices."
    ]
    
    suggestions = [
        "Pause 3 non-performing keywords",
        "Increase budget for top campaign",
        "Reduce bids on high ACOS keywords",
        "Restock low inventory products"
    ]
    
    return AIResponse(
        response=random.choice(responses),
        suggestions=random.sample(suggestions, 3)
    )

@api_router.get("/reports")
async def get_reports(user_id: str = Depends(get_current_user)):
    reports = [
        {
            "id": str(uuid.uuid4()),
            "report_name": "Weekly Sales Report",
            "report_type": "sales",
            "date_range": "Last 7 days",
            "generated_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "status": "ready"
        },
        {
            "id": str(uuid.uuid4()),
            "report_name": "Advertising Performance Report",
            "report_type": "advertising",
            "date_range": "Last 30 days",
            "generated_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "status": "ready"
        },
        {
            "id": str(uuid.uuid4()),
            "report_name": "Profit Analysis Report",
            "report_type": "profit",
            "date_range": "Last 30 days",
            "generated_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "status": "ready"
        }
    ]
    return {"reports": reports}

@api_router.get("/notifications")
async def get_notifications(user_id: str = Depends(get_current_user)):
    notifications = [
        {"id": str(uuid.uuid4()), "type": "warning", "message": "Low inventory alert: Wireless Headphones (12 units left)", "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(), "read": False},
        {"id": str(uuid.uuid4()), "type": "danger", "message": "High ad spend detected: Campaign 3 spent $450 today", "timestamp": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(), "read": False},
        {"id": str(uuid.uuid4()), "type": "success", "message": "Competitor price drop: Running Shoes competitor reduced price by $5", "timestamp": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(), "read": True},
        {"id": str(uuid.uuid4()), "type": "info", "message": "Weekly report generated successfully", "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), "read": True}
    ]
    return {"notifications": notifications}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()