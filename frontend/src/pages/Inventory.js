import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/utils/api';
import { AlertTriangle, Package, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';

const Inventory = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await apiClient.get('/inventory/alerts');
      setAlerts(response.data.alerts);
    } catch (error) {
      toast.error('Failed to load inventory alerts');
    } finally {
      setLoading(false);
    }
  };

  const criticalAlerts = alerts.filter(a => a.alert_level === 'critical').length;
  const warningAlerts = alerts.filter(a => a.alert_level === 'warning').length;

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="total-alerts-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Total Alerts</p>
                <p className="text-3xl font-bold text-slate-900 font-mono tracking-tight">{alerts.length}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-slate-50 text-slate-600 flex items-center justify-center">
                <Package size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="critical-alerts-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Critical Alerts</p>
                <p className="text-3xl font-bold text-rose-600 font-mono tracking-tight">{criticalAlerts}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertTriangle size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="warning-alerts-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Warning Alerts</p>
                <p className="text-3xl font-bold text-amber-600 font-mono tracking-tight">{warningAlerts}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-amber-50 text-amber-600 flex items-center justify-center">
                <TrendingDown size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Table */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="inventory-alerts-table">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Inventory Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">Product</th>
                  <th className="py-3 px-4 text-right">Current Stock</th>
                  <th className="py-3 px-4 text-right">Daily Velocity</th>
                  <th className="py-3 px-4 text-right">Days Until Stockout</th>
                  <th className="py-3 px-4 text-left">Marketplace</th>
                  <th className="py-3 px-4 text-center">Alert Level</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{alert.product_name}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{alert.current_stock}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{alert.daily_sales_velocity.toFixed(1)}/day</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono font-bold">{alert.days_until_stockout} days</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{alert.marketplace}</td>
                    <td className="py-3 px-4 text-center">
                      <Badge className={`${
                        alert.alert_level === 'critical' ? 'bg-rose-50 text-rose-600 border-rose-200' :
                        alert.alert_level === 'warning' ? 'bg-amber-50 text-amber-600 border-amber-200' :
                        'bg-indigo-50 text-indigo-600 border-indigo-200'
                      } rounded-sm text-xs uppercase tracking-wider font-bold`}>
                        {alert.alert_level}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Recommendation */}
      <Card className="bg-indigo-50 border border-indigo-200 shadow-sm rounded-sm">
        <CardContent className="p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle size={20} className="text-indigo-700 mt-0.5" />
            <div>
              <h4 className="font-semibold text-indigo-900 mb-1">AI Recommendation</h4>
              <p className="text-sm text-indigo-700">
                Consider reducing ad spend for products with less than 7 days of inventory to prevent stockouts and wasted advertising.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Inventory;
