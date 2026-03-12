#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class SellerOSAPITester:
    def __init__(self, base_url="https://campaign-autopilot-7.preview.emergentagent.com"):
        self.base_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        request_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            request_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=request_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=request_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=request_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out")
            return False, {}
        except requests.exceptions.ConnectionError:
            print(f"❌ Failed - Connection error")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_api_status(self):
        """Test if API is running"""
        success, response = self.run_test("API Status", "GET", "", 200)
        return success

    def test_register(self, email=None, full_name="Test User", password="test123"):
        """Test user registration"""
        if email is None:
            email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@test.com"
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data={"email": email, "full_name": full_name, "password": password}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            return True, email, password
        return False, email, password

    def test_login(self, email, password):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            return True
        return False

    def test_dashboard(self):
        """Test dashboard data retrieval"""
        success, response = self.run_test(
            "Dashboard Data",
            "GET",
            "dashboard",
            200
        )
        
        if success:
            required_fields = ['total_revenue', 'total_orders', 'net_profit', 'ad_spend', 'roas', 'acos']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing field: {field}")
                    return False
            print(f"   Dashboard has all required metrics")
        return success

    def test_orders(self):
        """Test orders endpoint"""
        success, response = self.run_test("Orders Data", "GET", "orders", 200)
        if success and 'orders' in response:
            print(f"   Found {len(response['orders'])} orders")
        return success

    def test_products(self):
        """Test products endpoint"""
        success, response = self.run_test("Products Data", "GET", "products", 200)
        if success and isinstance(response, list):
            print(f"   Found {len(response)} products")
            return True, response
        return False, []

    def test_campaigns(self):
        """Test campaigns endpoint"""
        success, response = self.run_test("Campaigns Data", "GET", "campaigns", 200)
        if success and 'campaigns' in response:
            print(f"   Found {len(response['campaigns'])} campaigns")
        return success

    def test_campaign_creation(self, products):
        """Test campaign creation"""
        if not products:
            print("❌ No products available for campaign creation")
            return False
            
        product = products[0]
        success, response = self.run_test(
            "Create Campaign",
            "POST",
            "campaigns/create",
            200,
            data={
                "product_id": product['id'],
                "product_name": product['name'],
                "auto_generate": True
            }
        )
        
        if success and 'campaigns' in response:
            print(f"   Generated {len(response['campaigns'])} campaigns")
        return success

    def test_profit_calculator(self):
        """Test profit calculation"""
        success, response = self.run_test("Profit Calculator", "GET", "profit/calculate", 200)
        if success and 'profit_data' in response:
            print(f"   Profit data for {len(response['profit_data'])} products")
        return success

    def test_inventory_alerts(self):
        """Test inventory alerts"""
        success, response = self.run_test("Inventory Alerts", "GET", "inventory/alerts", 200)
        if success and 'alerts' in response:
            print(f"   Found {len(response['alerts'])} inventory alerts")
        return success

    def test_competitors(self):
        """Test competitor data"""
        success, response = self.run_test("Competitor Data", "GET", "competitors", 200)
        if success and 'competitors' in response:
            print(f"   Found {len(response['competitors'])} competitors")
        return success

    def test_ai_copilot(self):
        """Test AI copilot functionality"""
        success, response = self.run_test(
            "AI Copilot",
            "POST",
            "ai-copilot",
            200,
            data={"message": "Help me optimize my campaigns"}
        )
        
        if success:
            if 'response' in response and 'suggestions' in response:
                print(f"   AI response: {response['response'][:50]}...")
                print(f"   Suggestions count: {len(response['suggestions'])}")
                return True
            else:
                print("❌ AI response missing required fields")
        return False

    def test_reports(self):
        """Test reports endpoint"""
        success, response = self.run_test("Reports Data", "GET", "reports", 200)
        if success and 'reports' in response:
            print(f"   Found {len(response['reports'])} reports")
        return success

    def test_notifications(self):
        """Test notifications endpoint"""
        success, response = self.run_test("Notifications", "GET", "notifications", 200)
        if success and 'notifications' in response:
            print(f"   Found {len(response['notifications'])} notifications")
        return success

    def test_store_connection(self):
        """Test store connection"""
        success, response = self.run_test(
            "Connect Store",
            "POST", 
            "stores",
            200,
            data={
                "marketplace": "Amazon",
                "store_name": "Test Store",
                "seller_id": "TEST123456"
            }
        )
        return success

    def test_get_stores(self):
        """Test get stores"""
        success, response = self.run_test("Get Stores", "GET", "stores", 200)
        return success

def main():
    print("🚀 Starting SellerOS API Testing...")
    print("=" * 50)
    
    # Initialize tester
    tester = SellerOSAPITester()
    
    # Test API status
    if not tester.test_api_status():
        print("\n❌ API is not accessible. Stopping tests.")
        return 1

    # Test registration
    reg_success, email, password = tester.test_register()
    if not reg_success:
        print("\n❌ Registration failed. Stopping tests.")
        return 1

    # Test all endpoints
    tester.test_dashboard()
    tester.test_orders()
    
    # Get products for campaign creation test
    products_success, products = tester.test_products()
    
    tester.test_campaigns()
    
    if products_success:
        tester.test_campaign_creation(products)
    
    tester.test_profit_calculator()
    tester.test_inventory_alerts()
    tester.test_competitors()
    tester.test_ai_copilot()
    tester.test_reports()
    tester.test_notifications()
    tester.test_store_connection()
    tester.test_get_stores()
    
    # Test login with created account
    if not tester.test_login(email, password):
        print("\n❌ Login with registered account failed")
        
    # Print results
    print(f"\n" + "=" * 50)
    print(f"📊 TEST RESULTS")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())