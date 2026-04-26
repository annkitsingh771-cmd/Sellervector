import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Orders from '@/pages/Orders';
import Advertising from '@/pages/Advertising';
import Campaigns from '@/pages/Campaigns';
import KeywordReport from '@/pages/KeywordReport';
import Profit from '@/pages/Profit';
import Inventory from '@/pages/Inventory';
import Products from '@/pages/Products';
import Competitors from '@/pages/Competitors';
import Reports from '@/pages/Reports';
import Settings from '@/pages/Settings';
import FBAShipmentPlanner from '@/pages/FBAShipmentPlanner';
import Subscription from '@/pages/Subscription';
import BudgetCalculator from '@/pages/BudgetCalculator';
import DayParting from '@/pages/DayParting';
import Optimization from '@/pages/Optimization';
import CampaignBuilder from '@/pages/CampaignBuilder';
import NotificationCenter from '@/pages/NotificationCenter';
import Layout from '@/components/Layout';
import '@/App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user,            setUser]            = useState(null);
  const [ready,           setReady]           = useState(false);

  useEffect(() => {
    try {
      const token    = localStorage.getItem('token');
      const userData = localStorage.getItem('user');

      // make sure token is a real JWT — not "undefined" or "null"
      const validToken = token && token !== 'undefined' && token !== 'null' && token.length > 20;
      const validUser  = userData && userData !== 'undefined' && userData !== 'null';

      if (validToken && validUser) {
        setIsAuthenticated(true);
        setUser(JSON.parse(userData));
      } else {
        // clear any bad data
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setIsAuthenticated(false);
      }
    } catch (e) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setIsAuthenticated(false);
    }
    setReady(true);
  }, []);

  const handleLogin = (token, userData) => {
    // safety check — don't save bad data
    if (!token || token === 'undefined' || !userData) {
      console.error('handleLogin called with invalid data', { token, userData });
      return;
    }
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    setIsAuthenticated(true);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.clear();
    setIsAuthenticated(false);
    setUser(null);
  };

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={isAuthenticated ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />}
          />
          <Route
            path="/"
            element={isAuthenticated ? <Layout user={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
          >
            <Route index                    element={<Dashboard />} />
            <Route path="orders"            element={<Orders />} />
            <Route path="advertising"       element={<Advertising />} />
            <Route path="campaigns"         element={<Campaigns />} />
            <Route path="campaign-builder"  element={<CampaignBuilder />} />
            <Route path="keyword-report"    element={<KeywordReport />} />
            <Route path="optimization"      element={<Optimization />} />
            <Route path="budget-calculator" element={<BudgetCalculator />} />
            <Route path="day-parting"       element={<DayParting />} />
            <Route path="profit"            element={<Profit />} />
            <Route path="inventory"         element={<Inventory />} />
            <Route path="products"          element={<Products />} />
            <Route path="competitors"       element={<Competitors />} />
            <Route path="reports"           element={<Reports />} />
            <Route path="fba-shipments"     element={<FBAShipmentPlanner />} />
            <Route path="notifications"     element={<NotificationCenter />} />
            <Route path="subscription"      element={<Subscription />} />
            <Route path="settings"          element={<Settings />} />
          </Route>
          <Route path="*" element={<Navigate to={isAuthenticated ? '/' : '/login'} replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </>
  );
}

export default App;
