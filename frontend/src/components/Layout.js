import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ShoppingCart, TrendingUp, Target, DollarSign, Package, Box, Users, FileText, Settings, Menu, X, Sparkles, Bell, ChevronDown, Key, Zap, Clock, Calculator, Rocket } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import AICopilot from '@/components/AICopilot';

const Layout = ({ user, onLogout }) => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [copilotOpen, setCopilotOpen] = useState(false);

  const menuItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/orders', icon: ShoppingCart, label: 'Orders' },
    { type: 'divider', label: 'PPC Automation' },
    { path: '/optimization', icon: Zap, label: 'Daily Optimization', badge: '5' },
    { path: '/campaign-builder', icon: Rocket, label: 'Campaign Builder' },
    { path: '/campaigns', icon: Target, label: 'Campaigns' },
    { path: '/advertising', icon: TrendingUp, label: 'Advertising' },
    { path: '/budget-calculator', icon: Calculator, label: 'Budget Calculator' },
    { path: '/day-parting', icon: Clock, label: 'Day Parting' },
    { path: '/keyword-report', icon: Key, label: 'Keyword Report' },
    { type: 'divider', label: 'Analytics & Inventory' },
    { path: '/profit', icon: DollarSign, label: 'Profit Calculator' },
    { path: '/inventory', icon: Package, label: 'Inventory' },
    { path: '/products', icon: Box, label: 'Products' },
    { path: '/fba-shipments', icon: Package, label: 'FBA Shipments' },
    { path: '/competitors', icon: Users, label: 'Competitors' },
    { type: 'divider', label: 'Settings' },
    { path: '/reports', icon: FileText, label: 'Reports' },
    { path: '/notifications', icon: Bell, label: 'Notifications' },
    { path: '/subscription', icon: Target, label: 'Subscription' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-0'
        } bg-slate-950 border-r border-slate-800 transition-all duration-150 flex-shrink-0`}
      >
        <div className="flex flex-col h-full">
          {/* Logo - Premium Design */}
          <div className="p-6 border-b border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full"></div>
                <img 
                  src="/sellervector-transparent.svg" 
                  alt="SellerVector" 
                  className="h-16 w-auto relative z-10 drop-shadow-lg" 
                />
              </div>
              <div className="text-center">
                <p className="text-white text-xs font-bold tracking-[0.2em] uppercase">Optimise Scale Dominate</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-3">
            {menuItems.map((item, index) => {
              if (item.type === 'divider') {
                return (
                  <div key={index} className="mt-4 mb-2 px-3">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{item.label}</p>
                  </div>
                );
              }
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
                  className={`flex items-center gap-3 px-3 py-2.5 mb-1 rounded-sm transition-all duration-150 ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <Icon size={18} strokeWidth={1.5} />
                  <span className="text-sm font-medium flex-1">{item.label}</span>
                  {item.badge && (
                    <Badge className="bg-rose-500 text-white text-xs px-1.5 min-w-[20px] h-5 flex items-center justify-center">
                      {item.badge}
                    </Badge>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-slate-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-sm flex items-center justify-center">
                <span className="text-white font-semibold text-sm">{user?.full_name?.charAt(0)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{user?.full_name}</p>
                <p className="text-slate-400 text-xs truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              onClick={onLogout}
              data-testid="logout-button"
              variant="ghost"
              className="w-full text-slate-300 hover:text-white hover:bg-slate-800 rounded-sm text-sm"
            >
              Logout
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="bg-white border-b border-slate-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                data-testid="toggle-sidebar-button"
                variant="ghost"
                size="icon"
                className="text-slate-600 hover:bg-slate-100 rounded-sm"
              >
                {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  {menuItems.find((item) => item.path === location.pathname)?.label || 'Dashboard'}
                </h1>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                data-testid="notifications-button"
                className="relative text-slate-600 hover:bg-slate-100 rounded-sm"
              >
                <Bell size={20} />
                <Badge className="absolute -top-1 -right-1 bg-rose-600 text-white text-xs px-1.5 min-w-[20px] h-5 flex items-center justify-center rounded-full">3</Badge>
              </Button>
              <Button
                onClick={() => setCopilotOpen(true)}
                data-testid="ai-copilot-button"
                className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
              >
                <Sparkles size={16} className="mr-2" />
                AI Copilot
              </Button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>

      {/* AI Copilot Sidebar */}
      <AICopilot isOpen={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
};

export default Layout;
