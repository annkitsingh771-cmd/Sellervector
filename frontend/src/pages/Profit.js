import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '@/utils/api';
import { DollarSign, TrendingDown, Calendar } from 'lucide-react';
import { toast } from 'sonner';

const Profit = () => {
  const [profitData, setProfitData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30');
  const [marketplace, setMarketplace] = useState('all');

  useEffect(() => {
    fetchProfit();
  }, [dateRange, marketplace]);

  const fetchProfit = async () => {
    try {
      const params = new URLSearchParams();
      if (marketplace !== 'all') params.append('marketplace', marketplace);
      params.append('days', dateRange);
      
      const response = await apiClient.get(`/profit/calculate?${params}`);
      setProfitData(response.data.profit_data || []);
    } catch (error) {
      toast.error('Failed to load profit data');
    } finally {
      setLoading(false);
    }
  };

  const totalNetProfit = profitData.reduce((sum, p) => sum + (p.net_profit || 0), 0);
  const totalTCOS = profitData.length > 0 ? (profitData.reduce((sum, p) => sum + (p.tcos || 0), 0) / profitData.length) : 0;
  const avgProfitMargin = profitData.length > 0 ? (profitData.reduce((sum, p) => sum + (p.profit_margin || 0), 0) / profitData.length) : 0;

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Filters */}
      <div className="flex gap-4">
        <Select value={dateRange} onValueChange={setDateRange}>
          <SelectTrigger className="w-48" data-testid="date-range-filter">
            <Calendar size={16} className="mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="30">Last 30 Days</SelectItem>
            <SelectItem value="60">Last 60 Days</SelectItem>
            <SelectItem value="90">Last 90 Days</SelectItem>
          </SelectContent>
        </Select>

        <Select value={marketplace} onValueChange={setMarketplace}>
          <SelectTrigger className="w-48" data-testid="marketplace-filter">
            <SelectValue placeholder="All Marketplaces" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Marketplaces</SelectItem>
            <SelectItem value="Amazon.com">Amazon.com</SelectItem>
            <SelectItem value="Flipkart">Flipkart</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="total-profit-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Total Net Profit</p>
                <p className="text-3xl font-bold text-emerald-600 font-mono tracking-tight">${totalNetProfit.toLocaleString()}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <DollarSign size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="avg-margin-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Average Profit Margin</p>
                <p className="text-3xl font-bold text-indigo-600 font-mono tracking-tight">{avgProfitMargin.toFixed(2)}%</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <TrendingDown size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="avg-tcos-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Average TCOS</p>
                <p className="text-3xl font-bold text-rose-600 font-mono tracking-tight">{totalTCOS.toFixed(2)}%</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-rose-50 text-rose-600 flex items-center justify-center">
                <TrendingDown size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Profit Breakdown */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="profit-breakdown-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Profit Breakdown by Product</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">Product</th>
                  <th className="py-3 px-4 text-right">Revenue</th>
                  <th className="py-3 px-4 text-right">Product Cost</th>
                  <th className="py-3 px-4 text-right">Referral Fee</th>
                  <th className="py-3 px-4 text-right">FBA Fee</th>
                  <th className="py-3 px-4 text-right">Ad Spend</th>
                  <th className="py-3 px-4 text-right">Storage</th>
                  <th className="py-3 px-4 text-right">Returns</th>
                  <th className="py-3 px-4 text-right">GST</th>
                  <th className="py-3 px-4 text-right">Other</th>
                  <th className="py-3 px-4 text-right">Net Profit</th>
                  <th className="py-3 px-4 text-right">Margin %</th>
                  <th className="py-3 px-4 text-right">TCOS %</th>
                </tr>
              </thead>
              <tbody>
                {profitData.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{item.product_name || 'N/A'}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${(item.revenue || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.product_cost || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.referral_fee || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.fba_fee || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.ad_spend || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.storage_fee || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.returns || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.gst || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${(item.other_charges || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono font-bold">${(item.net_profit || 0).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-indigo-600 text-right font-mono font-bold">{(item.profit_margin || 0).toFixed(2)}%</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono font-bold">{(item.tcos || 0).toFixed(2)}%</td>
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

export default Profit;
