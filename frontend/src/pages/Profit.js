import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/utils/api';
import { DollarSign, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';

const Profit = () => {
  const [profitData, setProfitData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfit();
  }, []);

  const fetchProfit = async () => {
    try {
      const response = await apiClient.get('/profit/calculate');
      setProfitData(response.data.profit_data);
    } catch (error) {
      toast.error('Failed to load profit data');
    } finally {
      setLoading(false);
    }
  };

  const totalNetProfit = profitData.reduce((sum, p) => sum + p.net_profit, 0);
  const avgProfitMargin = profitData.length > 0 ? (profitData.reduce((sum, p) => sum + p.profit_margin, 0) / profitData.length).toFixed(2) : 0;

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                <p className="text-3xl font-bold text-indigo-600 font-mono tracking-tight">{avgProfitMargin}%</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-indigo-50 text-indigo-600 flex items-center justify-center">
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
                  <th className="py-3 px-4 text-right">Referral Fee</th>
                  <th className="py-3 px-4 text-right">Fulfillment</th>
                  <th className="py-3 px-4 text-right">Ad Spend</th>
                  <th className="py-3 px-4 text-right">Product Cost</th>
                  <th className="py-3 px-4 text-right">Net Profit</th>
                  <th className="py-3 px-4 text-right">Margin</th>
                </tr>
              </thead>
              <tbody>
                {profitData.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{item.product_name}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${item.revenue.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${item.referral_fee.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${item.fulfillment_fee.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${item.ad_spend.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">-${item.product_cost.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono font-bold">${item.net_profit.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-indigo-600 text-right font-mono font-bold">{item.profit_margin.toFixed(2)}%</td>
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
