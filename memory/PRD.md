# SellerVector - Product Requirements Document

## Overview
SellerVector is an advanced multi-marketplace analytics and automation platform for e-commerce sellers, focused on Amazon PPC automation.

**Tagline:** Optimise Scale Dominate

## Core Problem
E-commerce sellers struggle with:
- Managing PPC campaigns across multiple marketplaces
- Tracking profitability with complex fee structures
- Optimizing ad spend for maximum ROAS
- Time-consuming manual campaign management

## Target Users
- Amazon sellers (primary)
- Multi-marketplace sellers (future)
- PPC agencies managing multiple seller accounts

---

## Implemented Features (as of Dec 2025)

### Authentication
- [x] User registration and login
- [x] JWT-based authentication
- [x] Demo account (demo@selleros.com / demo123)

### Dashboard
- [x] Key metrics display (Revenue, Orders, Profit, Ad Spend)
- [x] ROAS, ACOS, TCOS calculations
- [x] Date range filters (7, 14, 30, 60, 90 days)
- [x] Marketplace filter
- [x] Currency selector (USD/INR)
- [x] Orders trend chart
- [x] Revenue trend chart

### PPC Automation (NEW)
- [x] **Budget Calculator & ROAS Predictor**
  - Input: Budget, CPC, CVR, AOV, Target ACOS
  - Output: Estimated Clicks, Orders, Sales, ROAS, ACOS, Profit
  - AI Recommendations based on metrics
  
- [x] **ASIN/SKU Budget Planner**
  - Per-product daily budget management
  - Budget utilization tracking
  - Recommended budget suggestions
  
- [x] **Day Parting & Peak Hours**
  - 24-hour performance heatmap
  - Peak hours identification
  - Bid schedule with adjustments (-50% to +50%)
  - Weekly performance by day
  
- [x] **Daily Optimization Hub**
  - AI-generated optimization suggestions
  - One-click apply functionality
  - Priority-based sorting (High/Medium/Low)
  - Potential savings and revenue gain display
  
- [x] **Campaign Builder (2-Click)**
  - Step 1: Select Product
  - Step 2: Configure (Target ACOS/ROAS, Budget, Campaign Types)
  - Step 3: Review AI-generated campaigns
  - Step 4: Launch to Amazon

- [x] **Notification Center**
  - In-app notifications with history
  - Email notification toggle
  - Notification frequency settings
  - Alert type preferences (Optimization, Budget, Performance, Inventory)

### Advertising Analytics
- [x] Campaign list with metrics
- [x] ACOS, ROAS, CTR, CVR display
- [x] Keyword performance report (Hero/Wasted/Test)
- [x] Wasted spend detection

### Profit Calculator
- [x] Real profit calculation per product
- [x] Fee breakdown (Referral, FBA, Storage, Returns, GST)
- [x] TCOS formula: (Ad Spend / Revenue) * 100

### Inventory Management
- [x] Low stock alerts
- [x] Inventory ledger
- [x] FBA shipment planner
- [x] Bulk shipment CSV export

### Other Features
- [x] Product listing with ASIN/SKU
- [x] Competitor monitoring (mocked)
- [x] Reports page
- [x] Subscription plans page
- [x] AI Copilot sidebar

---

## Technical Architecture

### Frontend
- React 18 with React Router
- Tailwind CSS for styling
- Shadcn/UI components
- Recharts for visualizations

### Backend
- FastAPI (Python)
- MongoDB for user data
- JWT authentication
- Mock data generators (Faker)

### Data Flow
- All analytics data is currently MOCKED
- Ready for Amazon SP-API integration

---

## Upcoming Tasks (P0-P2)

### P0 - High Priority
- [ ] Amazon SP-API Integration (replace mocked data)
- [ ] Real campaign creation via API

### P1 - Important
- [ ] Stripe subscription integration
- [ ] Product cost input (manual + CSV bulk upload)
- [ ] Email notification delivery system

### P2 - Medium Priority
- [ ] Automatic campaign optimization (hands-free mode)
- [ ] Advanced keyword research tool
- [ ] BSR tracking
- [ ] Listing quality score

---

## Future Backlog

### Phase 2-6: Additional Marketplaces
- Flipkart, Meesho, eBay, Etsy, Walmart

### Advanced Features
- Real AI-powered campaign optimization
- Competitor ad spy
- Inventory forecasting with ML
- Weekly PDF/Excel reports
- Multi-user team management

---

## Demo Credentials
- Email: demo@selleros.com
- Password: demo123

## App URLs
- Frontend: https://campaign-autopilot-7.preview.emergentagent.com
- API: https://campaign-autopilot-7.preview.emergentagent.com/api

---

*Last Updated: December 2025*
