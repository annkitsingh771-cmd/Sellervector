import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ShoppingCart, TrendingUp, Target, DollarSign,
  Package, Box, Users, FileText, Settings, Menu, X, Sparkles,
  Bell, ChevronDown, Key, Zap, Clock, Calculator, Rocket, Store,
  RefreshCw, Plus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import AICopilot from '@/components/AICopilot';
import { apiClient } from '@/utils/api';

const Layout = ({ user, onLogout }) => {
  const location  = useLocation();
  const navigate  = useNavigate();
  const [sidebarOpen,   setSidebarOpen]   = useState(true);
  const [copilotOpen,   setCopilotOpen]   = useState(false);
  const [notifCount,    setNotifCount]    = useState(0);   // ← real count, not hardcoded 3
  const [optCount,      setOptCount]      = useState(0);   // ← real count, not hardcoded 5
  const [stores,        setStores]        = useState([]);
  const [activeStore,   setActiveStore]   = useState(null);
  const [showNotifDrop, setShowNotifDrop] = useState(false);
  const [notifications, setNotifications] = useState([]);

  // ── load stores & counts on mount ──────────────────────────
  useEffect(() => {
    fetchCounts();
    fetchStores();
    // poll every 60 s so badge stays fresh
    const t = setInterval(fetchCounts, 60_000);
    return () => clearInterval(t);
  }, []);

  const fetchCounts = async () => {
    try {
      const [nc, oc] = await Promise.all([
        apiClient.get('/notifications/count'),
        apiClient.get('/optimization/count'),
      ]);
      setNotifCount(nc.data.unread  ?? 0);
      setOptCount(  oc.data.pending ?? 0);
    } catch {
      // silently skip if network error
    }
  };

  const fetchStores = async () => {
    try {
      const res = await apiClient.get('/stores');
      const list = res.data || [];
      setStores(list);
      // restore previously selected store or default to first
      const saved = localStorage.getItem('activeStoreId');
      const found = list.find(s => s.id === saved);
      setActiveStore(found ? found.id : list[0]?.id || null);
    } catch { /* no stores yet */ }
  };

  const fetchNotifPreview = async () => {
    try {
      const res = await apiClient.get('/notifications/history');
      setNotifications(res.data.notifications?.slice(0, 5) || []);
    } catch { }
  };

  const handleStoreChange = (storeId) => {
    setActiveStore(storeId);
    localStorage.setItem('activeStoreId', storeId);
    // trigger a page refresh so all data re-fetches with the new store context
    window.dispatchEvent(new CustomEvent('storeChanged', { detail: { storeId } }));
  };

  const toggleNotifDrop = () => {
    if (!showNotifDrop) fetchNotifPreview();
    setShowNotifDrop(v => !v);
  };

  const markAllRead = async () => {
    try {
      await apiClient.post('/notifications/read-all');
      setNotifCount(0);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    } catch { }
  };

  // close notif dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (!e.target.closest('#notif-area')) setShowNotifDrop(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const menuItems = [
    { path: '/',                icon: LayoutDashboard, label: 'Dashboard' },
    { type: 'divider', label: 'PPC Automation' },
    { path: '/optimization',    icon: Zap,          label: 'Daily Optimization', countKey: 'opt' },
    { path: '/campaign-builder',icon: Rocket,        label: 'Campaign Builder' },
    { path: '/campaigns',       icon: Target,        label: 'Campaigns' },
    { path: '/advertising',     icon: TrendingUp,    label: 'Advertising' },
    { path: '/budget-calculator',icon: Calculator,   label: 'Budget Calculator' },
    { path: '/day-parting',     icon: Clock,         label: 'Day Parting' },
    { path: '/keyword-report',  icon: Key,           label: 'Keyword Report' },
    { type: 'divider', label: 'Analytics & Inventory' },
    { path: '/profit',    icon: DollarSign,  label: 'Profit Calculator' },
    { path: '/inventory', icon: Package,     label: 'Inventory' },
    { path: '/products',  icon: Box,         label: 'Products' },
    { path: '/fba-shipments', icon: Package, label: 'FBA Shipments' },
    { path: '/competitors',   icon: Users,   label: 'Competitors' },
    { type: 'divider', label: 'Settings' },
    { path: '/reports',        icon: FileText, label: 'Reports' },
    { path: '/notifications',  icon: Bell,     label: 'Notifications', countKey: 'notif' },
    { path: '/subscription',   icon: Target,   label: 'Subscription' },
    { path: '/settings',       icon: Settings, label: 'Settings' },
  ];

  const pageName = menuItems.find(i => i.path === location.pathname)?.label || 'Dashboard';

  const severityColor = (s) => {
    if (s === 'success') return '#22c55e';
    if (s === 'warning') return '#f59e0b';
    if (s === 'danger')  return '#ef4444';
    return '#6366f1';
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-slate-950 border-r border-slate-800 transition-all duration-150 flex-shrink-0 overflow-hidden`}>
        <div className="flex flex-col h-full w-64">
          {/* Logo */}
          <div className="p-6 border-b border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full" />
                <img src="/sellervector-transparent.svg" alt="SellerVector"
                     className="h-16 w-auto relative z-10 drop-shadow-lg" />
              </div>
              <p className="text-white text-xs font-bold tracking-[0.2em] uppercase">Optimise Scale Dominate</p>
            </div>
          </div>

          {/* Store Switcher — fixes account data mixing */}
          {stores.length > 0 && (
            <div className="px-4 py-3 border-b border-slate-800">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                <Store size={11} /> Active Store
              </p>
              {stores.length === 1 ? (
                <div className="px-3 py-2 bg-slate-800 rounded-sm">
                  <p className="text-white text-xs font-medium truncate">{stores[0].store_name}</p>
                  <p className="text-slate-400 text-[10px]">{stores[0].marketplace}</p>
                </div>
              ) : (
                <Select value={activeStore || ''} onValueChange={handleStoreChange}>
                  <SelectTrigger className="h-9 bg-slate-800 border-slate-700 text-white text-xs rounded-sm">
                    <SelectValue placeholder="Select store" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    {stores.map(s => (
                      <SelectItem key={s.id} value={s.id} className="text-white text-xs">
                        {s.store_name} <span className="text-slate-400 ml-1">({s.marketplace})</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}

          {/* Nav */}
          <nav className="flex-1 overflow-y-auto p-3">
            {menuItems.map((item, idx) => {
              if (item.type === 'divider') {
                return (
                  <div key={idx} className="mt-4 mb-2 px-3">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{item.label}</p>
                  </div>
                );
              }
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              const badge = item.countKey === 'opt' ? optCount
                          : item.countKey === 'notif' ? notifCount : 0;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={`nav-${item.label.toLowerCase().replace(/ /g, '-')}`}
                  className={`flex items-center gap-3 px-3 py-2.5 mb-1 rounded-sm transition-all duration-150 ${
                    isActive ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <Icon size={18} strokeWidth={1.5} />
                  <span className="text-sm font-medium flex-1">{item.label}</span>
                  {badge > 0 && (
                    <Badge className="bg-rose-500 text-white text-xs px-1.5 min-w-[20px] h-5 flex items-center justify-center">
                      {badge}
                    </Badge>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* User */}
          <div className="p-4 border-t border-slate-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-sm flex items-center justify-center">
                <span className="text-white font-semibold text-sm">{user?.full_name?.charAt(0) || '?'}</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{user?.full_name}</p>
                <p className="text-slate-400 text-xs truncate">{user?.email}</p>
              </div>
            </div>
            <Button onClick={onLogout} data-testid="logout-button" variant="ghost"
                    className="w-full text-slate-300 hover:text-white hover:bg-slate-800 rounded-sm text-sm">
              Logout
            </Button>
          </div>
        </div>
      </aside>

      {/* ── Main ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button onClick={() => setSidebarOpen(!sidebarOpen)} data-testid="toggle-sidebar-button"
                      variant="ghost" size="icon" className="text-slate-600 hover:bg-slate-100 rounded-sm">
                {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
              </Button>
              <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>
                {pageName}
              </h1>
            </div>

            <div className="flex items-center gap-3">
              {/* Connect store button in header */}
              <Button variant="outline" size="sm" className="text-slate-600 border-slate-200 rounded-sm text-xs"
                      onClick={() => navigate('/settings')}>
                <Plus size={13} className="mr-1" />
                Connect Store
              </Button>

              {/* Bell with real count */}
              <div id="notif-area" className="relative">
                <Button variant="ghost" size="icon" data-testid="notifications-button"
                        className="relative text-slate-600 hover:bg-slate-100 rounded-sm"
                        onClick={toggleNotifDrop}>
                  <Bell size={20} />
                  {notifCount > 0 && (
                    <Badge className="absolute -top-1 -right-1 bg-rose-600 text-white text-xs px-1.5 min-w-[20px] h-5 flex items-center justify-center rounded-full">
                      {notifCount > 99 ? '99+' : notifCount}
                    </Badge>
                  )}
                </Button>

                {/* Notification dropdown */}
                {showNotifDrop && (
                  <div className="absolute right-0 top-12 w-80 bg-white border border-slate-200 rounded-sm shadow-xl z-50">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
                      <span className="text-sm font-semibold text-slate-900">Notifications</span>
                      <button onClick={markAllRead}
                              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                        Mark all read
                      </button>
                    </div>
                    <div className="max-h-72 overflow-y-auto">
                      {notifications.length === 0 ? (
                        <p className="text-xs text-slate-400 text-center py-6">All caught up!</p>
                      ) : notifications.map(n => (
                        <div key={n.id} className={`px-4 py-3 border-b border-slate-50 hover:bg-slate-50 cursor-pointer ${!n.is_read ? 'bg-indigo-50/50' : ''}`}>
                          <div className="flex items-start gap-2">
                            <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                                 style={{ background: severityColor(n.severity) }} />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-semibold text-slate-900 truncate">{n.title}</p>
                              <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.message}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="px-4 py-2 border-t border-slate-100">
                      <button onClick={() => { navigate('/notifications'); setShowNotifDrop(false); }}
                              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium w-full text-center">
                        View all notifications
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <Button onClick={() => setCopilotOpen(true)} data-testid="ai-copilot-button"
                      className="bg-indigo-700 hover:bg-indigo-800 text-white rounded-sm font-medium transition-all duration-150 active:scale-95">
                <Sparkles size={16} className="mr-2" />
                AI Copilot
              </Button>
            </div>
          </div>
        </header>

        {/* Page content — key={pathname} prevents stale/blank renders */}
        <main key={location.pathname} className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>

      <AICopilot isOpen={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
};

export default Layout;
