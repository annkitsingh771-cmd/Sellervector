import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Bell, Mail, Settings, Zap, DollarSign, TrendingUp, Package, CheckCircle, AlertTriangle, Info, ExternalLink } from 'lucide-react';
import { apiClient } from '@/utils/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const NotificationCenter = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [settings, setSettings] = useState({
    email_notifications: true,
    in_app_notifications: true,
    daily_optimization_alerts: true,
    budget_alerts: true,
    performance_alerts: true,
    inventory_alerts: true,
    email_frequency: 'daily'
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNotifications();
    fetchSettings();
  }, []);

  const fetchNotifications = async () => {
    try {
      const response = await apiClient.get('/notifications/history');
      setNotifications(response.data.notifications);
      setUnreadCount(response.data.unread_count);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await apiClient.get('/notification-settings');
      setSettings(response.data.settings);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const updateSettings = async (key, value) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    try {
      await apiClient.patch('/notification-settings', newSettings);
      toast.success('Settings updated');
    } catch (error) {
      toast.error('Error updating settings');
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await apiClient.patch(`/notifications/${notificationId}/read`);
      setNotifications(prev => prev.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      ));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'optimization': return <Zap className="text-indigo-500" size={20} />;
      case 'budget': return <DollarSign className="text-amber-500" size={20} />;
      case 'performance': return <TrendingUp className="text-rose-500" size={20} />;
      case 'inventory': return <Package className="text-orange-500" size={20} />;
      case 'success': return <CheckCircle className="text-emerald-500" size={20} />;
      default: return <Info className="text-slate-500" size={20} />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'bg-rose-100 text-rose-700 border-rose-200';
      case 'medium': return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'low': return 'bg-slate-100 text-slate-700 border-slate-200';
      default: return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);
    
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-6" data-testid="notification-center-page">
      <Tabs defaultValue="notifications" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="notifications" className="relative">
            <Bell size={16} className="mr-2" />
            Notifications
            {unreadCount > 0 && (
              <Badge className="ml-2 bg-rose-600 text-white text-xs">{unreadCount}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings size={16} className="mr-2" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="text-indigo-600" size={20} />
                Notification History
              </CardTitle>
              <CardDescription>
                {unreadCount} unread notifications
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                </div>
              ) : (
                <div className="space-y-3">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`p-4 rounded-lg border transition-all cursor-pointer hover:shadow-sm ${
                        notification.read ? 'bg-white border-slate-200' : 'bg-indigo-50 border-indigo-200'
                      }`}
                      onClick={() => {
                        if (!notification.read) markAsRead(notification.id);
                        if (notification.action_url) navigate(notification.action_url);
                      }}
                      data-testid={`notification-${notification.id}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-white rounded-lg shadow-sm">
                          {getNotificationIcon(notification.type)}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className={`font-semibold ${notification.read ? 'text-slate-700' : 'text-slate-900'}`}>
                              {notification.title}
                            </h4>
                            <Badge className={getPriorityColor(notification.priority)}>
                              {notification.priority}
                            </Badge>
                            {!notification.read && (
                              <div className="w-2 h-2 bg-indigo-600 rounded-full"></div>
                            )}
                          </div>
                          <p className="text-sm text-slate-600">{notification.message}</p>
                          <p className="text-xs text-slate-400 mt-2">{formatTime(notification.timestamp)}</p>
                        </div>
                        {notification.action_url && (
                          <ExternalLink size={16} className="text-slate-400" />
                        )}
                      </div>
                    </div>
                  ))}

                  {notifications.length === 0 && (
                    <div className="text-center py-8 text-slate-500">
                      <Bell size={48} className="mx-auto mb-4 opacity-50" />
                      <p>No notifications yet</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Notification Channels */}
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="text-indigo-600" size={20} />
                  Notification Channels
                </CardTitle>
                <CardDescription>
                  Choose how you want to receive notifications
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-100 rounded-lg">
                      <Bell className="text-indigo-600" size={20} />
                    </div>
                    <div>
                      <Label className="font-medium">In-App Notifications</Label>
                      <p className="text-sm text-slate-500">Show alerts within the app</p>
                    </div>
                  </div>
                  <Switch
                    checked={settings.in_app_notifications}
                    onCheckedChange={(checked) => updateSettings('in_app_notifications', checked)}
                    data-testid="toggle-in-app"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-100 rounded-lg">
                      <Mail className="text-emerald-600" size={20} />
                    </div>
                    <div>
                      <Label className="font-medium">Email Notifications</Label>
                      <p className="text-sm text-slate-500">Receive alerts via email</p>
                    </div>
                  </div>
                  <Switch
                    checked={settings.email_notifications}
                    onCheckedChange={(checked) => updateSettings('email_notifications', checked)}
                    data-testid="toggle-email"
                  />
                </div>

                {settings.email_notifications && (
                  <div className="pl-11">
                    <Label className="text-sm text-slate-600">Email Frequency</Label>
                    <Select
                      value={settings.email_frequency}
                      onValueChange={(value) => updateSettings('email_frequency', value)}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="realtime">Real-time</SelectItem>
                        <SelectItem value="daily">Daily Digest</SelectItem>
                        <SelectItem value="weekly">Weekly Summary</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Alert Types */}
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="text-amber-600" size={20} />
                  Alert Types
                </CardTitle>
                <CardDescription>
                  Choose which alerts you want to receive
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-100 rounded-lg">
                      <Zap className="text-indigo-600" size={20} />
                    </div>
                    <div>
                      <Label className="font-medium">Daily Optimization Alerts</Label>
                      <p className="text-sm text-slate-500">AI-powered optimization suggestions</p>
                    </div>
                  </div>
                  <Switch
                    checked={settings.daily_optimization_alerts}
                    onCheckedChange={(checked) => updateSettings('daily_optimization_alerts', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-100 rounded-lg">
                      <DollarSign className="text-amber-600" size={20} />
                    </div>
                    <div>
                      <Label className="font-medium">Budget Alerts</Label>
                      <p className="text-sm text-slate-500">Budget pacing and overspend warnings</p>
                    </div>
                  </div>
                  <Switch
                    checked={settings.budget_alerts}
                    onCheckedChange={(checked) => updateSettings('budget_alerts', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-rose-100 rounded-lg">
                      <TrendingUp className="text-rose-600" size={20} />
                    </div>
                    <div>
                      <Label className="font-medium">Performance Alerts</Label>
                      <p className="text-sm text-slate-500">ACOS/ROAS threshold warnings</p>
                    </div>
                  </div>
                  <Switch
                    checked={settings.performance_alerts}
                    onCheckedChange={(checked) => updateSettings('performance_alerts', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-orange-100 rounded-lg">
                      <Package className="text-orange-600" size={20} />
                    </div>
                    <div>
                      <Label className="font-medium">Inventory Alerts</Label>
                      <p className="text-sm text-slate-500">Low stock and out-of-stock warnings</p>
                    </div>
                  </div>
                  <Switch
                    checked={settings.inventory_alerts}
                    onCheckedChange={(checked) => updateSettings('inventory_alerts', checked)}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default NotificationCenter;
