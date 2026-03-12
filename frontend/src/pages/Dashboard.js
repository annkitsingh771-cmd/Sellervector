import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/utils/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, AlertTriangle, Target, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { toast } from 'sonner';

const MetricCard = ({ title, value = 0, change, icon: Icon, trend, format = 'number' }) => {
  const isPositive = trend === 'up';
  const safeValue = value || 0;
  const formattedValue = format === 'currency' ? `$${safeValue.toLocaleString()}` : 
                        format === 'percent' ? `${safeValue}%` : 
                        safeValue.toLocaleString();

  return (
    <Card className="bg-white border border-slate-200 shadow-sm rounded-sm hover:border-indigo-300 transition-colors duration-200" data-testid={`metric-card-${title.toLowerCase().replace(' ', '-')}`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">{title}</p>
            <p className="text-2xl font-bold text-slate-900 font-mono tracking-tight">{formattedValue}</p>
            {change && (
              <div className="flex items-center gap-1 mt-2">
                {isPositive ? <ArrowUpRight size={14} className="text-emerald-600" /> : <ArrowDownRight size={14} className="text-rose-600" />}
                <span className={`text-xs font-semibold ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {change}
                </span>
                <span className="text-xs text-slate-500">vs last period</span>
              </div>
            )}
          </div>
          <div className={`w-12 h-12 rounded-sm flex items-center justify-center ${
            trend === 'up' ? 'bg-emerald-50 text-emerald-600' : 
            trend === 'down' ? 'bg-rose-50 text-rose-600' : 
            'bg-indigo-50 text-indigo-600'
          }`}>
            <Icon size={24} strokeWidth={1.5} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const response = await apiClient.get('/dashboard');
      setData(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-indigo-700 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Revenue"
          value={data?.total_revenue || 0}
          change="+12.5%"
          icon={DollarSign}
          trend="up"
          format="currency"
        />
        <MetricCard
          title="Total Orders"
          value={data?.total_orders || 0}
          change="+8.2%"
          icon={ShoppingCart}
          trend="up"
        />
        <MetricCard
          title="Net Profit"
          value={data?.net_profit || 0}
          change="+15.3%"
          icon={TrendingUp}
          trend="up"
          format="currency"
        />
        <MetricCard
          title="Ad Spend"
          value={data?.ad_spend || 0}
          change="-5.1%"
          icon={Target}
          trend="down"
          format="currency"
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="roas-card">
          <CardContent className="p-5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">ROAS</p>
            <p className="text-3xl font-bold text-emerald-600 font-mono tracking-tight">{data?.roas || 0}x</p>
            <p className="text-xs text-slate-500 mt-1">Return on Ad Spend</p>
          </CardContent>
        </Card>
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="acos-card">
          <CardContent className="p-5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">ACOS</p>
            <p className="text-3xl font-bold text-indigo-600 font-mono tracking-tight">{data?.acos || 0}%</p>
            <p className="text-xs text-slate-500 mt-1">Advertising Cost of Sales</p>
          </CardContent>
        </Card>
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="tcos-card">
          <CardContent className="p-5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">TCOS</p>
            <p className="text-3xl font-bold text-rose-600 font-mono tracking-tight">{data?.tcos || 0}%</p>
            <p className="text-xs text-slate-500 mt-1">Total Cost of Sales</p>
          </CardContent>
        </Card>
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="alerts-card">
          <CardContent className="p-5">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Low Inventory Alerts</p>
            <p className="text-3xl font-bold text-amber-600 font-mono tracking-tight">{data?.low_inventory_alerts || 0}</p>
            <p className="text-xs text-slate-500 mt-1">Products need restocking</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="orders-chart-card">
          <CardHeader>
            <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Orders Trend (Last 30 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data?.orders_chart || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: 'none',
                    borderRadius: '2px',
                    color: '#fff',
                    fontSize: '12px'
                  }}
                />
                <Line type="monotone" dataKey="orders" stroke="#4338ca" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="revenue-chart-card">
          <CardHeader>
            <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Revenue Trend (Last 30 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data?.revenue_chart || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: 'none',
                    borderRadius: '2px',
                    color: '#fff',
                    fontSize: '12px'
                  }}
                />
                <Bar dataKey="revenue" fill="#10b981" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Top Products */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="top-products-card">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Top Selling Products</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            data-testid="view-all-products-button"
            className="text-indigo-700 hover:bg-indigo-50 rounded-sm"
          >
            View All
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">Product</th>
                  <th className="py-3 px-4 text-right">Revenue</th>
                  <th className="py-3 px-4 text-right">Orders</th>
                  <th className="py-3 px-4 text-right">Profit</th>
                  <th className="py-3 px-4 text-right">Stock</th>
                </tr>
              </thead>
              <tbody>
                {data?.top_products?.map((product, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{product.name || 'N/A'}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${(product.revenue || 0).toLocaleString()}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{product.orders || 0}</td>
                    <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono">${(product.net_profit || 0).toLocaleString()}</td>
                    <td className="py-3 px-4 text-right">
                      <Badge className={`${
                        (product.stock_level || 0) < 50 ? 'bg-amber-50 text-amber-600 border-amber-200' : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                      } rounded-sm font-mono text-xs`}>
                        {product.stock_level || 0}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
