"""
Test suite for PPC Automation features:
- Budget Calculator & ROAS Predictor
- Day Parting & Peak Hours Analysis
- Daily Optimization Hub
- Campaign Builder
- Notification System
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthentication:
    """Authentication tests for demo account"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for demo account"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@selleros.com",
            "password": "demo123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_login_success(self):
        """Test demo account login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@selleros.com",
            "password": "demo123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == "demo@selleros.com"


class TestBudgetCalculator:
    """Budget Calculator & ROAS Predictor tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@selleros.com",
            "password": "demo123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_budget_calculator_basic(self, auth_headers):
        """Test budget calculator with basic inputs"""
        response = requests.post(f"{BASE_URL}/api/budget-calculator", 
            json={
                "budget": 1000,
                "cpc": 0.50,
                "cvr": 10,
                "avg_order_value": 50,
                "target_acos": 30
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "input" in data
        assert "predictions" in data
        assert "recommendations" in data
        
        # Verify predictions
        predictions = data["predictions"]
        assert "estimated_clicks" in predictions
        assert "estimated_orders" in predictions
        assert "estimated_sales" in predictions
        assert "estimated_roas" in predictions
        assert "estimated_acos" in predictions
        assert "profit_after_ads" in predictions
        
        # Verify calculations
        assert predictions["estimated_clicks"] == 2000  # 1000 / 0.50
        assert predictions["estimated_orders"] == 200   # 2000 * 0.10
        assert predictions["estimated_sales"] == 10000  # 200 * 50
        
    def test_budget_calculator_high_acos(self, auth_headers):
        """Test budget calculator with high ACOS scenario"""
        response = requests.post(f"{BASE_URL}/api/budget-calculator", 
            json={
                "budget": 500,
                "cpc": 1.50,
                "cvr": 5,
                "avg_order_value": 30,
                "target_acos": 20
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have recommendations for high ACOS
        assert len(data["recommendations"]) > 0
        
    def test_budget_planner_products(self, auth_headers):
        """Test ASIN/SKU budget planner"""
        response = requests.get(f"{BASE_URL}/api/budget-planner/products", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "budget_plans" in data
        assert len(data["budget_plans"]) > 0
        
        # Verify budget plan structure
        plan = data["budget_plans"][0]
        assert "product_id" in plan
        assert "product_name" in plan
        assert "asin" in plan
        assert "daily_budget" in plan
        assert "monthly_budget" in plan
        assert "current_daily_spend" in plan
        assert "budget_utilization" in plan
        assert "recommended_budget" in plan
        assert "acos" in plan
        assert "roas" in plan
        
    def test_update_product_budget(self, auth_headers):
        """Test updating product budget"""
        # First get products
        response = requests.get(f"{BASE_URL}/api/budget-planner/products", 
            headers=auth_headers
        )
        product_id = response.json()["budget_plans"][0]["product_id"]
        
        # Update budget
        response = requests.patch(f"{BASE_URL}/api/budget-planner/products/{product_id}", 
            json={"daily_budget": 75.00},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Budget updated successfully"


class TestDayParting:
    """Day Parting & Peak Hours Analysis tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@selleros.com",
            "password": "demo123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_dayparting_analysis(self, auth_headers):
        """Test day parting analysis endpoint"""
        response = requests.get(f"{BASE_URL}/api/dayparting/analysis", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "hourly_data" in data
        assert "daily_data" in data
        assert "peak_hours" in data
        assert "recommendations" in data
        
        # Verify hourly data (24 hours)
        assert len(data["hourly_data"]) == 24
        
        # Verify hourly data structure
        hour_data = data["hourly_data"][0]
        assert "hour" in hour_data
        assert "hour_label" in hour_data
        assert "sales" in hour_data
        assert "orders" in hour_data
        assert "clicks" in hour_data
        assert "spend" in hour_data
        assert "acos" in hour_data
        assert "is_peak" in hour_data
        
        # Verify daily data (7 days)
        assert len(data["daily_data"]) == 7
        
        # Verify peak hours exist
        assert len(data["peak_hours"]) > 0
        
    def test_dayparting_schedule_get(self, auth_headers):
        """Test getting day parting schedule"""
        response = requests.get(f"{BASE_URL}/api/dayparting/schedule", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "schedule" in data
        assert len(data["schedule"]) == 24  # 24 hours
        
        # Verify schedule structure
        slot = data["schedule"][0]
        assert "hour" in slot
        assert "hour_label" in slot
        assert "bid_adjustment" in slot
        assert "enabled" in slot
        
    def test_dayparting_schedule_update(self, auth_headers):
        """Test updating day parting schedule"""
        schedule = [{"hour": i, "bid_adjustment": 10 if i in [10, 11] else 0, "enabled": True} for i in range(24)]
        
        response = requests.post(f"{BASE_URL}/api/dayparting/schedule", 
            json={"schedule": schedule},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Day parting schedule updated"


class TestOptimization:
    """Daily Optimization Hub tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@selleros.com",
            "password": "demo123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_optimization_suggestions(self, auth_headers):
        """Test getting optimization suggestions"""
        response = requests.get(f"{BASE_URL}/api/optimization/suggestions", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "suggestions" in data
        assert "summary" in data
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_suggestions" in summary
        assert "high_priority" in summary
        assert "potential_savings" in summary
        assert "potential_revenue_gain" in summary
        
        # Verify suggestions exist
        assert len(data["suggestions"]) > 0
        
        # Verify suggestion structure
        suggestion = data["suggestions"][0]
        assert "id" in suggestion
        assert "type" in suggestion
        assert "priority" in suggestion
        assert "title" in suggestion
        assert "description" in suggestion
        assert "campaign_name" in suggestion
        assert "action" in suggestion
        assert "status" in suggestion
        
    def test_apply_single_optimization(self, auth_headers):
        """Test applying a single optimization"""
        # First get suggestions
        response = requests.get(f"{BASE_URL}/api/optimization/suggestions", 
            headers=auth_headers
        )
        suggestion_id = response.json()["suggestions"][0]["id"]
        
        # Apply optimization
        response = requests.post(f"{BASE_URL}/api/optimization/apply/{suggestion_id}", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Optimization applied successfully"
        assert data["status"] == "applied"
        
    def test_apply_all_optimizations(self, auth_headers):
        """Test applying multiple optimizations"""
        # Get suggestions
        response = requests.get(f"{BASE_URL}/api/optimization/suggestions", 
            headers=auth_headers
        )
        suggestion_ids = [s["id"] for s in response.json()["suggestions"][:3]]
        
        # Apply all
        response = requests.post(f"{BASE_URL}/api/optimization/apply-all", 
            json={"suggestion_ids": suggestion_ids},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["applied_count"] == len(suggestion_ids)


class TestCampaignBuilder:
    """Campaign Builder tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@selleros.com",
            "password": "demo123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_products_for_campaign(self, auth_headers):
        """Test getting products for campaign builder"""
        response = requests.get(f"{BASE_URL}/api/campaign-builder/products", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "products" in data
        assert len(data["products"]) > 0
        
        # Verify product structure
        product = data["products"][0]
        assert "id" in product
        assert "name" in product
        assert "asin" in product
        assert "sku" in product
        assert "price" in product
        
    def test_generate_ai_campaigns(self, auth_headers):
        """Test AI campaign generation"""
        # Get a product first
        response = requests.get(f"{BASE_URL}/api/campaign-builder/products", 
            headers=auth_headers
        )
        product = response.json()["products"][0]
        
        # Generate campaigns
        response = requests.post(f"{BASE_URL}/api/campaign-builder/generate", 
            json={
                "product_id": product["id"],
                "product_name": product["name"],
                "target_acos": 30,
                "target_roas": 3.5,
                "daily_budget": 50,
                "campaign_types": ["sponsored_products", "sponsored_brands", "sponsored_display"]
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "product_id" in data
        assert "product_name" in data
        assert "campaigns" in data
        assert "strategy_summary" in data
        
        # Verify campaigns generated
        assert len(data["campaigns"]) > 0
        
        # Verify campaign structure
        campaign = data["campaigns"][0]
        assert "id" in campaign
        assert "campaign_type" in campaign
        assert "campaign_name" in campaign
        assert "daily_budget" in campaign
        assert "status" in campaign
        
    def test_launch_campaigns(self, auth_headers):
        """Test launching campaigns"""
        # Generate campaigns first
        response = requests.get(f"{BASE_URL}/api/campaign-builder/products", 
            headers=auth_headers
        )
        product = response.json()["products"][0]
        
        response = requests.post(f"{BASE_URL}/api/campaign-builder/generate", 
            json={
                "product_id": product["id"],
                "product_name": product["name"],
                "target_acos": 30,
                "target_roas": 3.5,
                "daily_budget": 50,
                "campaign_types": ["sponsored_products"]
            },
            headers=auth_headers
        )
        campaigns = response.json()["campaigns"]
        
        # Launch campaigns
        response = requests.post(f"{BASE_URL}/api/campaign-builder/launch", 
            json={"campaigns": campaigns},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "launched_campaigns" in data
        assert len(data["launched_campaigns"]) > 0
        
        # Verify launched campaign structure
        launched = data["launched_campaigns"][0]
        assert "campaign_id" in launched
        assert "campaign_name" in launched
        assert launched["status"] == "live"


class TestNotificationSystem:
    """Notification System tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@selleros.com",
            "password": "demo123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_notification_settings(self, auth_headers):
        """Test getting notification settings"""
        response = requests.get(f"{BASE_URL}/api/notification-settings", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "settings" in data
        settings = data["settings"]
        
        # Verify settings structure
        assert "email_notifications" in settings
        assert "in_app_notifications" in settings
        assert "daily_optimization_alerts" in settings
        assert "budget_alerts" in settings
        assert "performance_alerts" in settings
        assert "inventory_alerts" in settings
        assert "email_frequency" in settings
        
    def test_update_notification_settings(self, auth_headers):
        """Test updating notification settings"""
        response = requests.patch(f"{BASE_URL}/api/notification-settings", 
            json={
                "email_notifications": False,
                "in_app_notifications": True,
                "daily_optimization_alerts": True,
                "budget_alerts": False
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Notification settings updated"
        
    def test_get_notification_history(self, auth_headers):
        """Test getting notification history"""
        response = requests.get(f"{BASE_URL}/api/notifications/history", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "notifications" in data
        assert "unread_count" in data
        
        # Verify notifications exist
        assert len(data["notifications"]) > 0
        
        # Verify notification structure
        notification = data["notifications"][0]
        assert "id" in notification
        assert "type" in notification
        assert "priority" in notification
        assert "title" in notification
        assert "message" in notification
        assert "timestamp" in notification
        assert "read" in notification
        
    def test_mark_notification_read(self, auth_headers):
        """Test marking notification as read"""
        # Get notifications first
        response = requests.get(f"{BASE_URL}/api/notifications/history", 
            headers=auth_headers
        )
        notification_id = response.json()["notifications"][0]["id"]
        
        # Mark as read
        response = requests.patch(f"{BASE_URL}/api/notifications/{notification_id}/read", 
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Notification marked as read"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
