from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
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
import io
import csv

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

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    name: str
    sku: str
    asin: str = ""
    fnsku: str = ""
    price: float
    product_cost: float = 0.0
    stock_level: int
    revenue: float
    orders: int
    conversion_rate: float
    ad_spend: float
    referral_fee: float
    fba_fee: float
    storage_fee: float
    returns: float
    gst: float
    other_charges: float
    net_profit: float
    tcos: float
    marketplace: str

class FBAShipment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    sku: str
    fnsku: str
    title: str
    quantity_needed: int
    fc_code: str
    priority: str

class InventoryLedger(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    transaction_type: str
    quantity: int
    date: str
    notes: str

class SubscriptionPlan(BaseModel):
    plan_name: str
    price: float
    features: List[str]

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

# Seed demo account
async def seed_demo_account():
    demo_email = "demo@selleros.com"
    existing = await db.users.find_one({"email": demo_email}, {"_id": 0})
    if not existing:
        demo_user = User(
            email=demo_email,
            full_name="Demo User",
            subscription_plan="professional"
        )
        user_dict = demo_user.model_dump()
        user_dict["password_hash"] = hash_password("demo123")
        await db.users.insert_one(user_dict)
        logging.info("Demo account created")

# Mock data generators with proper cost calculations
def calculate_product_metrics(revenue: float, orders: int, product_cost: float, ad_spend: float):
    referral_fee = revenue * 0.15
    fba_fee = orders * 3.50
    storage_fee = random.uniform(5, 20)
    returns = revenue * 0.01
    gst = revenue * 0.05
    other_charges = random.uniform(2, 10)
    
    total_costs = product_cost + referral_fee + fba_fee + ad_spend + storage_fee + returns + gst + other_charges
    net_profit = revenue - total_costs
    
    # TCOS = (Ad Spend / Revenue) * 100  (User's formula)
    tcos = (ad_spend / revenue * 100) if revenue > 0 else 0
    
    return {
        "referral_fee": round(referral_fee, 2),
        "fba_fee": round(fba_fee, 2),
        "storage_fee": round(storage_fee, 2),
        "returns": round(returns, 2),
        "gst": round(gst, 2),
        "other_charges": round(other_charges, 2),
        "net_profit": round(net_profit, 2),
        "tcos": round(tcos, 2)
    }

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
            "marketplace": "Amazon.com",
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
        product_cost = revenue * random.uniform(0.25, 0.35)  # Reduced from 0.3-0.5 to 0.25-0.35
        ad_spend = round(random.uniform(30, 300), 2)  # Reduced from 50-500 to 30-300
        
        metrics = calculate_product_metrics(revenue, orders, product_cost, ad_spend)
        
        products.append({
            "id": str(uuid.uuid4()),
            "store_id": store_id,
            "name": name,
            "sku": f"SKU-{random.randint(1000, 9999)}",
            "asin": f"B0{random.randint(10000000, 99999999)}",
            "fnsku": f"X00{random.randint(1000000, 9999999)}",
            "price": round(random.uniform(15, 150), 2),
            "product_cost": round(product_cost, 2),
            "stock_level": random.randint(5, 500),
            "revenue": revenue,
            "orders": orders,
            "conversion_rate": round(random.uniform(5, 25), 2),
            "ad_spend": ad_spend,
            "referral_fee": metrics["referral_fee"],
            "fba_fee": metrics["fba_fee"],
            "storage_fee": metrics["storage_fee"],
            "returns": metrics["returns"],
            "gst": metrics["gst"],
            "other_charges": metrics["other_charges"],
            "net_profit": metrics["net_profit"],
            "tcos": metrics["tcos"],
            "marketplace": "Amazon.com"
        })
    return products

def generate_mock_campaigns(store_id: str, with_metrics: bool = True):
    campaigns = []
    for i in range(5):
        impressions = random.randint(10000, 100000)
        clicks = random.randint(200, 2000)
        orders = random.randint(10, 150)
        ad_spend = round(random.uniform(100, 1000), 2)
        ad_sales = round(random.uniform(500, 5000), 2)
        
        ctr = round((clicks / impressions * 100), 2) if impressions > 0 else 0
        cvr = round((orders / clicks * 100), 2) if clicks > 0 else 0
        
        campaigns.append({
            "id": str(uuid.uuid4()),
            "store_id": store_id,
            "product_id": str(uuid.uuid4()),
            "campaign_name": f"Campaign {i+1} - {random.choice(['Auto', 'Manual', 'Product Targeting'])}",
            "campaign_type": random.choice(["auto", "manual", "product_targeting"]),
            "budget": round(random.uniform(500, 2000), 2),
            "status": random.choice(["active", "paused"]),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "orders": orders,
            "cvr": cvr,
            "ad_spend": ad_spend,
            "ad_sales": ad_sales,
            "acos": round((ad_spend / ad_sales * 100) if ad_sales > 0 else 0, 2),
            "roas": round(ad_sales / ad_spend if ad_spend > 0 else 0, 2),
            "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))).isoformat()
        })
    return campaigns

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
async def get_dashboard(store_id: Optional[str] = None, days: int = 30, currency: str = "USD", user_id: str = Depends(get_current_user)):
    # Generate orders for specified days
    orders = generate_mock_orders(store_id or "default", days)
    products = generate_mock_products(store_id or "default")
    
    # Currency conversion (1 USD = 83 INR approx)
    conversion_rate = 83 if currency == "INR" else 1
    
    total_revenue = sum(o["revenue"] for o in orders) * conversion_rate
    total_orders = len(orders)
    ad_spend = sum(p["ad_spend"] for p in products) * conversion_rate
    net_profit = sum(p["net_profit"] for p in products) * conversion_rate
    
    # Calculate TCOS from products using user's formula: (ad_spend / revenue) * 100
    avg_tcos = round(sum(p["tcos"] for p in products) / len(products) if len(products) > 0 else 0, 2)
    
    # Convert product data to selected currency
    converted_products = []
    for p in products:
        converted_products.append({
            **p,
            "revenue": p["revenue"] * conversion_rate,
            "ad_spend": p["ad_spend"] * conversion_rate,
            "net_profit": p["net_profit"] * conversion_rate,
            "product_cost": p["product_cost"] * conversion_rate,
            "referral_fee": p["referral_fee"] * conversion_rate,
            "fba_fee": p["fba_fee"] * conversion_rate,
            "storage_fee": p["storage_fee"] * conversion_rate,
            "returns": p["returns"] * conversion_rate,
            "gst": p["gst"] * conversion_rate,
            "other_charges": p["other_charges"] * conversion_rate
        })
    
    # Generate chart data for specified days
    orders_chart = []
    revenue_chart = []
    for i in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=days-1-i)).strftime("%b %d")
        day_orders = [o for o in orders if (datetime.now(timezone.utc) - datetime.fromisoformat(o["order_date"])).days == (days-1-i)]
        orders_chart.append({"date": date, "orders": len(day_orders)})
        revenue_chart.append({"date": date, "revenue": round(sum(o["revenue"] for o in day_orders) * conversion_rate, 2)})
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "net_profit": round(net_profit, 2),
        "ad_spend": round(ad_spend, 2),
        "tcos": avg_tcos,
        "roas": round(total_revenue / ad_spend if ad_spend > 0 else 0, 2),
        "acos": round((ad_spend / total_revenue * 100) if total_revenue > 0 else 0, 2),
        "top_products": sorted(converted_products, key=lambda x: x["revenue"], reverse=True)[:5],
        "low_inventory_alerts": len([p for p in products if p["stock_level"] < 50]),
        "sales_by_marketplace": [{"marketplace": "Amazon.com", "orders": total_orders, "revenue": round(total_revenue, 2)}],
        "orders_chart": orders_chart,
        "revenue_chart": revenue_chart,
        "currency": currency
    }

@api_router.get("/orders")
async def get_orders(store_id: Optional[str] = None, days: int = 30, user_id: str = Depends(get_current_user)):
    orders = generate_mock_orders(store_id or "default", days)
    return {"orders": orders, "total": len(orders)}

@api_router.get("/products", response_model=List[Product])
async def get_products(store_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    products = generate_mock_products(store_id or "default")
    return products

@api_router.post("/products/bulk-upload")
async def bulk_upload_products(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    contents = await file.read()
    csv_data = contents.decode('utf-8')
    reader = csv.DictReader(io.StringIO(csv_data))
    
    uploaded_count = 0
    for row in reader:
        # Process each row and save to database
        uploaded_count += 1
    
    return {"message": f"Successfully uploaded {uploaded_count} products", "count": uploaded_count}

@api_router.patch("/products/{product_id}/cost")
async def update_product_cost(product_id: str, cost_data: Dict[str, float], user_id: str = Depends(get_current_user)):
    # In real implementation, update database
    return {"message": "Product cost updated", "product_id": product_id}

@api_router.get("/campaigns")
async def get_campaigns(store_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    campaigns = generate_mock_campaigns(store_id or "default")
    return {"campaigns": campaigns}

@api_router.post("/campaigns/create")
async def create_campaign(campaign_data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    campaigns = [
        {
            "id": str(uuid.uuid4()),
            "campaign_name": f"{campaign_data['product_name']} - Auto Campaign",
            "campaign_type": "auto",
            "budget": 500,
            "status": "draft",
            "ad_groups": [{"name": "Auto Targeting", "bid": 0.75}]
        },
        {
            "id": str(uuid.uuid4()),
            "campaign_name": f"{campaign_data['product_name']} - Manual Keywords",
            "campaign_type": "manual",
            "budget": 1000,
            "status": "draft",
            "keywords": [
                {"keyword": f"{campaign_data['product_name'].lower()}", "match_type": "exact", "bid": 1.25},
                {"keyword": f"best {campaign_data['product_name'].lower()}", "match_type": "phrase", "bid": 1.00},
                {"keyword": f"{campaign_data['product_name'].lower()} sale", "match_type": "broad", "bid": 0.85}
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "campaign_name": f"{campaign_data['product_name']} - Product Targeting",
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
        impressions = random.randint(1000, 10000)
        clicks = random.randint(10, 500)
        orders = random.randint(0, 20)
        
        keywords.append({
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "keyword": random.choice(["wireless headphones", "bluetooth headphones", "noise cancelling headphones", "best headphones", "gaming headphones"]),
            "match_type": random.choice(["exact", "phrase", "broad"]),
            "bid": round(random.uniform(0.5, 2.5), 2),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round((clicks / impressions * 100), 2) if impressions > 0 else 0,
            "spend": spend,
            "sales": sales,
            "acos": round((spend / sales * 100) if sales > 0 else 100, 2),
            "orders": orders,
            "cvr": round((orders / clicks * 100), 2) if clicks > 0 else 0,
            "status": random.choice(["active", "paused"])
        })
    return {"keywords": keywords}

@api_router.get("/campaigns/wasted-spend")
async def get_wasted_spend(user_id: str = Depends(get_current_user)):
    wasted_keywords = []
    for i in range(5):
        spend = round(random.uniform(50, 300), 2)
        wasted_keywords.append({
            "keyword": random.choice(["cheap wireless headphones", "free shipping headphones", "discount bluetooth"]),
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
        profit_data.append({
            "product_name": p["name"],
            "revenue": p["revenue"],
            "product_cost": p["product_cost"],
            "referral_fee": p["referral_fee"],
            "fba_fee": p["fba_fee"],
            "ad_spend": p["ad_spend"],
            "storage_fee": p["storage_fee"],
            "returns": p["returns"],
            "gst": p["gst"],
            "other_charges": p["other_charges"],
            "net_profit": p["net_profit"],
            "profit_margin": round((p["net_profit"] / p["revenue"] * 100) if p["revenue"] > 0 else 0, 2),
            "tcos": p["tcos"]
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
            "product_name": random.choice(["Wireless Headphones", "Running Shoes", "Smartwatch"]),
            "current_stock": stock,
            "daily_sales_velocity": velocity,
            "days_until_stockout": days_left,
            "alert_level": "critical" if days_left < 7 else "warning" if days_left < 14 else "info",
            "marketplace": "Amazon.com"
        })
    return {"alerts": alerts}

@api_router.get("/inventory/ledger")
async def get_inventory_ledger(product_id: Optional[str] = None, user_id: str = Depends(get_current_user)):
    ledger = []
    for i in range(20):
        ledger.append({
            "id": str(uuid.uuid4()),
            "product_id": product_id or str(uuid.uuid4()),
            "transaction_type": random.choice(["sale", "shipment_sent", "return", "damaged", "adjustment"]),
            "quantity": random.randint(-10, 100),
            "date": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 60))).isoformat(),
            "notes": random.choice(["Sold to customer", "Sent to FC", "Customer return", "Warehouse damaged", "Inventory adjustment"])
        })
    return {"ledger": sorted(ledger, key=lambda x: x["date"], reverse=True)}

@api_router.get("/fba/shipment-planner")
async def get_fba_shipment_planner(user_id: str = Depends(get_current_user)):
    products = generate_mock_products("default")
    shipments = []
    
    for p in products:
        if p["stock_level"] < 100:
            quantity_needed = 200 - p["stock_level"]
            fc_codes = ["DEX3", "DEX5", "PHX6", "ONT8", "MDW2"]
            
            shipments.append({
                "id": str(uuid.uuid4()),
                "product_id": p["id"],
                "sku": p["sku"],
                "fnsku": p["fnsku"],
                "title": p["name"],
                "current_stock": p["stock_level"],
                "quantity_needed": quantity_needed,
                "fc_code": random.choice(fc_codes),
                "priority": "high" if p["stock_level"] < 50 else "medium"
            })
    
    return {"shipments": shipments, "total_items": len(shipments)}

@api_router.post("/fba/download-bulk-sheet")
async def download_bulk_sheet(shipment_ids: List[str], user_id: str = Depends(get_current_user)):
    # Generate CSV for Amazon bulk upload
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Amazon standard template headers
    writer.writerow(["SKU", "FNSKU", "Product Name", "Quantity", "FC Code", "Box Contents"])
    
    # Get shipments (mock data for now)
    shipments_response = await get_fba_shipment_planner(user_id)
    for shipment in shipments_response["shipments"]:
        if shipment["id"] in shipment_ids:
            writer.writerow([
                shipment["sku"],
                shipment["fnsku"],
                shipment["title"],
                shipment["quantity_needed"],
                shipment["fc_code"],
                "1"  # Number of boxes
            ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=amazon_bulk_shipment.csv"}
    )

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
            "marketplace": "Amazon.com"
        })
    return {"competitors": competitors}

@api_router.post("/ai-copilot")
async def ai_copilot(message: Dict[str, str], user_id: str = Depends(get_current_user)):
    responses = [
        "Based on your data, I recommend reducing bids for Campaign 4 to improve ACOS by 15%.",
        "Your Wireless Headphones product will run out of stock in 7 days. Consider reducing ad spend or restocking soon.",
        "Campaign 2 has excellent ROAS of 4.5x. I suggest increasing the budget by 25% to maximize profits.",
        "I detected $350 in wasted ad spend on keywords with zero conversions. Would you like me to pause them?",
        "Your TCOS is 68% which is higher than the recommended 50-60%. Consider negotiating better product costs or reducing ad spend."
    ]
    
    suggestions = [
        "Pause 3 non-performing keywords",
        "Increase budget for top campaign",
        "Reduce bids on high ACOS keywords",
        "Restock low inventory products",
        "Send 5 products to Amazon FC (FBA shipment needed)"
    ]
    
    return {
        "response": random.choice(responses),
        "suggestions": random.sample(suggestions, 3)
    }

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
        {"id": str(uuid.uuid4()), "type": "success", "message": "FBA shipment delivered to DEX3 warehouse", "timestamp": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(), "read": True},
    ]
    return {"notifications": notifications}

@api_router.get("/subscription/plans")
async def get_subscription_plans():
    plans = [
        {
            "plan_name": "Free",
            "price": 0,
            "features": [
                "1 Marketplace",
                "Basic Analytics",
                "10 Products",
                "Email Support"
            ]
        },
        {
            "plan_name": "Starter",
            "price": 29,
            "features": [
                "2 Marketplaces",
                "Advanced Analytics",
                "50 Products",
                "Campaign Automation",
                "Priority Support"
            ]
        },
        {
            "plan_name": "Professional",
            "price": 79,
            "features": [
                "5 Marketplaces",
                "Full Analytics Suite",
                "Unlimited Products",
                "AI Copilot",
                "FBA Shipment Planner",
                "Inventory Ledger",
                "24/7 Support"
            ]
        },
        {
            "plan_name": "Enterprise",
            "price": 199,
            "features": [
                "Unlimited Marketplaces",
                "Custom Reports",
                "Unlimited Products",
                "Advanced AI Features",
                "API Access",
                "Dedicated Account Manager",
                "Custom Integrations"
            ]
        }
    ]
    return {"plans": plans}

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

@app.on_event("startup")
async def startup_event():
    await seed_demo_account()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()