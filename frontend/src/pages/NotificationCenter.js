import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Bell, Mail, Settings, Zap, DollarSign, TrendingUp, Package, CheckCircle, AlertTriangle, Info } from 'lucide-react';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';

const NotificationCenter = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount,   setUnreadCount]   = useState(0);
  const [settings, setSettings] = useState({
    email_notifications: true, in_app_notifications: true,
    daily_optimization_alerts: true, budget_alerts: true,
    performance_alerts: true, inventory_alerts: true, email_frequency: 'daily',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchNotifications(); fetchSettings(); }, []);

  const fetchNotifications = async () => {
    try {
      // ← correct endpoint: /notifications/history
      const res = await apiClient.get('/notifications/history');
      setNotifications(res.data.notifications || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (err) { console.error('Notification fetch error', err); }
    finally       { setLoading(false); }
  };

  const fetchSettings = async () => {
    try {
      const res = await apiClient.get('/notification-settings');
      if (res.data.settings) setSettings(res.data.settings);
    } catch { /* use defaults */ }
  };

  const updateSettings = async (key, value) => {
    const updated = { ...settings, [key]: value };
    setSettings(updated);
    try {
      await apiClient.patch('/notification-settings', updated);
      toast.success('Settings updated');
    } catch { toast.error('Failed to save settings'); }
  };

  const markAllRead = async () => {
    try {
      await apiClient.post('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast.success('All marked as read');
    } catch { toast.error('Failed to mark as read'); }
  };

  const markOneRead = async (id) => {
    try {
      await apiClient.post(`/notifications/${id}/read`);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch { }
  };

  const severityIcon = (s) => {
    if (s === 'success') return <CheckCircle size={16} className="text-emerald-500" />;
    if (s === 'warning') return <AlertTriangle size={16} className="text-amber-500" />;
    if (s === 'danger')  return <AlertTriangle size={16} className="text-rose-500" />;
    return <Info size={16} className="text-indigo-500" />;
  };

  const severityBadge = (s) => ({
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    danger:  'bg-rose-100 text-rose-700',
    info:    'bg-indigo-100 text-indigo-700',
  }[s] || 'bg-slate-100 text-slate-700');

  const formatTime = (iso) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60)    return 'just now';
    if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return d.toLocaleDateString();
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
    </div>
  );

  return (
    <div className="space-y-6 fade-in">
      <Tabs defaultValue="notifications" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell size={16} />
            Notifications
            {unreadCount > 0 && (
              <Badge className="bg-rose-500 text-white text-xs px-1.5 ml-1 min-w-[20px] h-5 flex items-center justify-center">
                {unreadCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings size={16} /> Settings
          </TabsTrigger>
        </TabsList>

        {/* ── Notifications tab ── */}
        <TabsContent value="notifications">
          <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  Notifications
                </CardTitle>
                <CardDescription>{unreadCount} unread</CardDescription>
              </div>
              {unreadCount > 0 && (
                <Button variant="outline" size="sm" onClick={markAllRead}
                        className="text-slate-600 border-slate-200 rounded-sm text-xs">
                  Mark all read
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {notifications.length === 0 ? (
                <div className="text-center py-12">
                  <CheckCircle size={48} className="mx-auto text-emerald-400 mb-4" />
                  <p className="text-slate-600 font-medium">You're all caught up!</p>
                  <p className="text-sm text-slate-400 mt-1">No notifications yet.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {notifications.map(n => (
                    <div key={n.id}
                         onClick={() => !n.is_read && markOneRead(n.id)}
                         className={`flex items-start gap-3 p-4 rounded-sm border cursor-pointer transition-colors ${
                           n.is_read
                             ? 'border-slate-100 bg-white hover:bg-slate-50'
                             : 'border-indigo-100 bg-indigo-50/40 hover:bg-indigo-50'
                         }`}>
                      <div className="mt-0.5">{severityIcon(n.severity)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-slate-900">{n.title}</p>
                          <Badge className={`${severityBadge(n.severity)} text-xs rounded-sm`}>{n.severity}</Badge>
                          {!n.is_read && <div className="w-2 h-2 rounded-full bg-indigo-500" />}
                        </div>
                        <p className="text-sm text-slate-600 mt-0.5">{n.message}</p>
                        <p className="text-xs text-slate-400 mt-1">{formatTime(n.created_at)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Settings tab ── */}
        <TabsContent value="settings">
          <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
            <CardHeader>
              <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Notification Settings
              </CardTitle>
              <CardDescription>Control how and when you receive alerts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {[
                { key: 'email_notifications',       label: 'Email Notifications',       desc: 'Receive notifications by email', icon: Mail },
                { key: 'in_app_notifications',       label: 'In-App Notifications',       desc: 'Show notifications in the app',  icon: Bell },
                { key: 'daily_optimization_alerts',  label: 'Daily Optimization Alerts',  desc: 'New bid/budget suggestions',     icon: Zap },
                { key: 'budget_alerts',              label: 'Budget Alerts',              desc: 'When campaigns hit budget cap',  icon: DollarSign },
                { key: 'performance_alerts',         label: 'Performance Alerts',         desc: 'ACoS/ROAS threshold breaches',   icon: TrendingUp },
                { key: 'inventory_alerts',           label: 'Inventory Alerts',           desc: 'Low stock warnings',             icon: Package },
              ].map(({ key, label, desc, icon: Icon }) => (
                <div key={key} className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 bg-indigo-50 rounded-sm flex items-center justify-center">
                      <Icon size={18} className="text-indigo-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-900">{label}</p>
                      <p className="text-xs text-slate-500">{desc}</p>
                    </div>
                  </div>
                  <Switch checked={!!settings[key]} onCheckedChange={v => updateSettings(key, v)} />
                </div>
              ))}

              <div className="pt-2">
                <Label className="text-sm font-medium text-slate-900 mb-2 block">Email Frequency</Label>
                <Select value={settings.email_frequency}
                        onValueChange={v => updateSettings('email_frequency', v)}>
                  <SelectTrigger className="w-48 border-slate-200 rounded-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="realtime">Real-time</SelectItem>
                    <SelectItem value="daily">Daily Digest</SelectItem>
                    <SelectItem value="weekly">Weekly Summary</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default NotificationCenter;
