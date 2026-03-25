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
    return {"message": "SellerVector API", "status": "running"}

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

# ============= NEW PPC AUTOMATION ENDPOINTS =============

# Budget Calculator & ROAS Predictor
@api_router.post("/budget-calculator")
async def calculate_budget(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    budget = float(data.get("budget", 1000))
    cpc = float(data.get("cpc", 0.50))
    cvr = float(data.get("cvr", 10))  # Conversion rate %
    avg_order_value = float(data.get("avg_order_value", 50))
    target_acos = float(data.get("target_acos", 30))
    
    # Calculations
    estimated_clicks = int(budget / cpc) if cpc > 0 else 0
    estimated_orders = int(estimated_clicks * (cvr / 100))
    estimated_sales = round(estimated_orders * avg_order_value, 2)
    estimated_roas = round(estimated_sales / budget, 2) if budget > 0 else 0
    estimated_acos = round((budget / estimated_sales * 100), 2) if estimated_sales > 0 else 0
    profit_after_ads = round(estimated_sales - budget, 2)
    
    # Recommendations
    recommendations = []
    if estimated_acos > target_acos:
        recommendations.append(f"Your estimated ACOS ({estimated_acos}%) exceeds target ({target_acos}%). Consider reducing CPC or improving CVR.")
    if estimated_roas < 2:
        recommendations.append("ROAS below 2x - campaigns may not be profitable. Review product pricing or reduce ad spend.")
    if cvr < 8:
        recommendations.append("Low conversion rate. Improve listing quality, images, and reviews to boost CVR.")
    if estimated_roas >= 4:
        recommendations.append("Excellent ROAS potential! Consider increasing budget to scale.")
    
    return {
        "input": {"budget": budget, "cpc": cpc, "cvr": cvr, "avg_order_value": avg_order_value, "target_acos": target_acos},
        "predictions": {
            "estimated_clicks": estimated_clicks,
            "estimated_orders": estimated_orders,
            "estimated_sales": estimated_sales,
            "estimated_roas": estimated_roas,
            "estimated_acos": estimated_acos,
            "profit_after_ads": profit_after_ads
        },
        "recommendations": recommendations
    }

# ASIN/SKU Budget Planning
@api_router.get("/budget-planner/products")
async def get_product_budget_plans(user_id: str = Depends(get_current_user)):
    products = generate_mock_products("default")
    budget_plans = []
    
    for p in products:
        daily_budget = round(random.uniform(20, 100), 2)
        monthly_budget = daily_budget * 30
        current_spend = round(random.uniform(daily_budget * 0.5, daily_budget * 1.2), 2)
        
        budget_plans.append({
            "product_id": p["id"],
            "product_name": p["name"],
            "asin": p["asin"],
            "sku": p["sku"],
            "daily_budget": daily_budget,
            "monthly_budget": round(monthly_budget, 2),
            "current_daily_spend": current_spend,
            "budget_utilization": round((current_spend / daily_budget * 100), 1) if daily_budget > 0 else 0,
            "recommended_budget": round(daily_budget * 1.2 if p["conversion_rate"] > 15 else daily_budget * 0.9, 2),
            "acos": round(random.uniform(15, 40), 2),
            "roas": round(random.uniform(2, 6), 2)
        })
    
    return {"budget_plans": budget_plans}

@api_router.patch("/budget-planner/products/{product_id}")
async def update_product_budget(product_id: str, data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"message": "Budget updated successfully", "product_id": product_id, "new_budget": data.get("daily_budget")}

# Day Parting & Peak Hours Analysis
@api_router.get("/dayparting/analysis")
async def get_dayparting_analysis(user_id: str = Depends(get_current_user)):
    # Generate hourly performance data
    hourly_data = []
    peak_hours = [10, 11, 14, 15, 20, 21]  # Mock peak hours
    
    for hour in range(24):
        is_peak = hour in peak_hours
        base_sales = 15 if is_peak else 5
        base_orders = 3 if is_peak else 1
        
        hourly_data.append({
            "hour": hour,
            "hour_label": f"{hour:02d}:00",
            "sales": round(base_sales + random.uniform(-3, 8), 2),
            "orders": base_orders + random.randint(0, 3),
            "clicks": random.randint(20, 100) if is_peak else random.randint(5, 30),
            "spend": round(random.uniform(5, 25) if is_peak else random.uniform(2, 10), 2),
            "acos": round(random.uniform(18, 35), 2),
            "is_peak": is_peak
        })
    
    # Day of week performance
    daily_data = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in days:
        is_weekend = day in ["Saturday", "Sunday"]
        daily_data.append({
            "day": day,
            "sales": round(random.uniform(150, 400) if is_weekend else random.uniform(80, 250), 2),
            "orders": random.randint(15, 40) if is_weekend else random.randint(8, 25),
            "spend": round(random.uniform(40, 100), 2),
            "acos": round(random.uniform(20, 35), 2),
            "is_high_performance": is_weekend
        })
    
    return {
        "hourly_data": hourly_data,
        "daily_data": daily_data,
        "peak_hours": peak_hours,
        "recommendations": [
            "Increase bids by 20% during peak hours (10-11 AM, 2-3 PM, 8-9 PM)",
            "Reduce bids by 30% during low-traffic hours (12 AM - 6 AM)",
            "Weekend performance is 40% higher - consider increasing weekend budgets"
        ]
    }

@api_router.get("/dayparting/schedule")
async def get_dayparting_schedule(user_id: str = Depends(get_current_user)):
    schedule = []
    for hour in range(24):
        schedule.append({
            "hour": hour,
            "hour_label": f"{hour:02d}:00 - {(hour+1)%24:02d}:00",
            "bid_adjustment": 20 if hour in [10, 11, 14, 15, 20, 21] else (-30 if hour < 6 else 0),
            "enabled": True
        })
    return {"schedule": schedule}

@api_router.post("/dayparting/schedule")
async def update_dayparting_schedule(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    return {"message": "Day parting schedule updated", "schedule": data.get("schedule")}

# Daily Optimization Hub
@api_router.get("/optimization/suggestions")
async def get_optimization_suggestions(user_id: str = Depends(get_current_user)):
    suggestions = [
        {
            "id": str(uuid.uuid4()),
            "type": "bid_decrease",
            "priority": "high",
            "title": "Reduce bid for high ACOS keyword",
            "description": "Keyword 'wireless bluetooth headphones' has 45% ACOS. Reduce bid from $1.25 to $0.95.",
            "campaign_name": "Headphones - Manual Campaign",
            "keyword": "wireless bluetooth headphones",
            "current_bid": 1.25,
            "suggested_bid": 0.95,
            "current_acos": 45.2,
            "expected_acos": 32.5,
            "estimated_savings": 85.50,
            "action": "reduce_bid",
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "bid_increase",
            "priority": "high",
            "title": "Increase bid for profitable keyword",
            "description": "Keyword 'best running shoes' has 12% ACOS with high CVR. Increase bid to capture more traffic.",
            "campaign_name": "Running Shoes - Manual",
            "keyword": "best running shoes",
            "current_bid": 0.85,
            "suggested_bid": 1.15,
            "current_acos": 12.3,
            "expected_acos": 15.0,
            "estimated_revenue_gain": 250.00,
            "action": "increase_bid",
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "pause_keyword",
            "priority": "medium",
            "title": "Pause non-converting keyword",
            "description": "Keyword 'cheap headphones free shipping' spent $120 with 0 sales. Recommend pausing.",
            "campaign_name": "Headphones - Broad Match",
            "keyword": "cheap headphones free shipping",
            "spend": 120.00,
            "sales": 0,
            "clicks": 180,
            "action": "pause_keyword",
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "budget_increase",
            "priority": "medium",
            "title": "Increase campaign budget",
            "description": "Campaign 'Smartwatch - Auto' is hitting budget cap by 2 PM daily. Missing 35% of potential traffic.",
            "campaign_name": "Smartwatch - Auto",
            "current_budget": 50.00,
            "suggested_budget": 75.00,
            "estimated_additional_sales": 180.00,
            "action": "increase_budget",
            "status": "pending"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "negative_keyword",
            "priority": "low",
            "title": "Add negative keyword",
            "description": "Search term 'free headphones' is wasting spend. Add as negative keyword.",
            "campaign_name": "Headphones - Auto Campaign",
            "keyword": "free headphones",
            "spend": 45.00,
            "sales": 0,
            "action": "add_negative",
            "status": "pending"
        }
    ]
    
    summary = {
        "total_suggestions": len(suggestions),
        "high_priority": len([s for s in suggestions if s["priority"] == "high"]),
        "potential_savings": sum(s.get("estimated_savings", 0) for s in suggestions),
        "potential_revenue_gain": sum(s.get("estimated_revenue_gain", 0) for s in suggestions)
    }
    
    return {"suggestions": suggestions, "summary": summary}

@api_router.post("/optimization/apply/{suggestion_id}")
async def apply_optimization(suggestion_id: str, user_id: str = Depends(get_current_user)):
    # In real implementation, this would call Amazon API
    return {
        "message": "Optimization applied successfully",
        "suggestion_id": suggestion_id,
        "status": "applied",
        "applied_at": datetime.now(timezone.utc).isoformat()
    }

@api_router.post("/optimization/apply-all")
async def apply_all_optimizations(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    suggestion_ids = data.get("suggestion_ids", [])
    return {
        "message": f"Applied {len(suggestion_ids)} optimizations",
        "applied_count": len(suggestion_ids),
        "applied_at": datetime.now(timezone.utc).isoformat()
    }

# AI Campaign Builder
@api_router.get("/campaign-builder/products")
async def get_products_for_campaign(user_id: str = Depends(get_current_user)):
    products = generate_mock_products("default")
    return {"products": [{"id": p["id"], "name": p["name"], "asin": p["asin"], "sku": p["sku"], "price": p["price"]} for p in products]}

@api_router.post("/campaign-builder/generate")
async def generate_ai_campaign(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    product_id = data.get("product_id")
    product_name = data.get("product_name", "Product")
    target_acos = data.get("target_acos", 30)
    target_roas = data.get("target_roas", 3.5)
    daily_budget = data.get("daily_budget", 50)
    campaign_types = data.get("campaign_types", ["sponsored_products", "sponsored_brands", "sponsored_display"])
    
    generated_campaigns = []
    
    if "sponsored_products" in campaign_types:
        # Auto Campaign
        generated_campaigns.append({
            "id": str(uuid.uuid4()),
            "campaign_type": "Sponsored Products - Auto",
            "campaign_name": f"{product_name} - SP Auto",
            "targeting_type": "auto",
            "daily_budget": round(daily_budget * 0.3, 2),
            "default_bid": round(0.75 * (target_acos / 30), 2),
            "ad_groups": [
                {"name": "Close Match", "bid": round(0.85 * (target_acos / 30), 2)},
                {"name": "Loose Match", "bid": round(0.65 * (target_acos / 30), 2)},
                {"name": "Substitutes", "bid": round(0.70 * (target_acos / 30), 2)},
                {"name": "Complements", "bid": round(0.60 * (target_acos / 30), 2)}
            ],
            "status": "draft"
        })
        
        # Manual - Exact Match
        generated_campaigns.append({
            "id": str(uuid.uuid4()),
            "campaign_type": "Sponsored Products - Manual Exact",
            "campaign_name": f"{product_name} - SP Exact",
            "targeting_type": "manual",
            "match_type": "exact",
            "daily_budget": round(daily_budget * 0.35, 2),
            "keywords": [
                {"keyword": product_name.lower(), "bid": round(1.20 * (target_acos / 30), 2), "match_type": "exact"},
                {"keyword": f"best {product_name.lower()}", "bid": round(1.10 * (target_acos / 30), 2), "match_type": "exact"},
                {"keyword": f"{product_name.lower()} for sale", "bid": round(1.00 * (target_acos / 30), 2), "match_type": "exact"}
            ],
            "status": "draft"
        })
        
        # Manual - Phrase Match
        generated_campaigns.append({
            "id": str(uuid.uuid4()),
            "campaign_type": "Sponsored Products - Manual Phrase",
            "campaign_name": f"{product_name} - SP Phrase",
            "targeting_type": "manual",
            "match_type": "phrase",
            "daily_budget": round(daily_budget * 0.2, 2),
            "keywords": [
                {"keyword": product_name.lower(), "bid": round(0.90 * (target_acos / 30), 2), "match_type": "phrase"},
                {"keyword": f"buy {product_name.lower()}", "bid": round(0.85 * (target_acos / 30), 2), "match_type": "phrase"}
            ],
            "status": "draft"
        })
    
    if "sponsored_brands" in campaign_types:
        generated_campaigns.append({
            "id": str(uuid.uuid4()),
            "campaign_type": "Sponsored Brands",
            "campaign_name": f"{product_name} - SB Video",
            "targeting_type": "keyword",
            "daily_budget": round(daily_budget * 0.1, 2),
            "creative_type": "video",
            "keywords": [
                {"keyword": product_name.lower(), "bid": round(1.50 * (target_acos / 30), 2), "match_type": "broad"}
            ],
            "status": "draft"
        })
    
    if "sponsored_display" in campaign_types:
        generated_campaigns.append({
            "id": str(uuid.uuid4()),
            "campaign_type": "Sponsored Display",
            "campaign_name": f"{product_name} - SD Retargeting",
            "targeting_type": "audience",
            "daily_budget": round(daily_budget * 0.05, 2),
            "audiences": ["Views remarketing", "Purchases remarketing"],
            "status": "draft"
        })
    
    return {
        "product_id": product_id,
        "product_name": product_name,
        "target_metrics": {"target_acos": target_acos, "target_roas": target_roas},
        "total_daily_budget": daily_budget,
        "campaigns": generated_campaigns,
        "strategy_summary": f"Created {len(generated_campaigns)} campaigns optimized for {target_acos}% ACOS target. Budget distributed across campaign types for maximum coverage."
    }

@api_router.post("/campaign-builder/launch")
async def launch_campaigns(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    campaigns = data.get("campaigns", [])
    # In real implementation, this would call Amazon Advertising API
    launched = []
    for campaign in campaigns:
        launched.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("campaign_name"),
            "status": "live",
            "launched_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {
        "message": f"Successfully launched {len(launched)} campaigns",
        "launched_campaigns": launched
    }

# Notification Settings & History
@api_router.get("/notification-settings")
async def get_notification_settings(user_id: str = Depends(get_current_user)):
    settings = {
        "email_notifications": True,
        "in_app_notifications": True,
        "daily_optimization_alerts": True,
        "budget_alerts": True,
        "performance_alerts": True,
        "inventory_alerts": True,
        "email_frequency": "daily",  # daily, weekly, realtime
        "email_address": "demo@selleros.com"
    }
    return {"settings": settings}

@api_router.patch("/notification-settings")
async def update_notification_settings(data: Dict[str, Any], user_id: str = Depends(get_current_user)):
    # In real implementation, save to database
    return {"message": "Notification settings updated", "settings": data}

@api_router.get("/notifications/history")
async def get_notification_history(user_id: str = Depends(get_current_user)):
    notifications = [
        {
            "id": str(uuid.uuid4()),
            "type": "optimization",
            "priority": "high",
            "title": "Daily Optimization Ready",
            "message": "5 optimization suggestions available. Potential savings: $285.50",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "read": False,
            "action_url": "/optimization"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "budget",
            "priority": "medium",
            "title": "Budget Alert",
            "message": "Campaign 'Headphones Auto' reached 90% of daily budget by 2 PM",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            "read": False,
            "action_url": "/budget-planner"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "performance",
            "priority": "high",
            "title": "High ACOS Alert",
            "message": "Campaign 'Running Shoes Manual' ACOS increased to 42% (target: 30%)",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            "read": True,
            "action_url": "/campaigns"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "success",
            "priority": "low",
            "title": "Campaign Launched",
            "message": "Successfully launched 3 new campaigns for 'Smartwatch Pro'",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(),
            "read": True,
            "action_url": "/campaigns"
        },
        {
            "id": str(uuid.uuid4()),
            "type": "inventory",
            "priority": "medium",
            "title": "Low Inventory Warning",
            "message": "Wireless Headphones stock at 15 units. Consider reducing ad spend or restocking.",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
            "read": True,
            "action_url": "/inventory"
        }
    ]
    
    return {
        "notifications": notifications,
        "unread_count": len([n for n in notifications if not n["read"]])
    }

@api_router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user_id: str = Depends(get_current_user)):
    return {"message": "Notification marked as read", "notification_id": notification_id}

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