import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/utils/api';
import { TrendingUp, Target, MousePointer, Eye, DollarSign } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { toast } from 'sonner';

const Advertising = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const response = await apiClient.get('/campaigns');
      setCampaigns(response.data.campaigns);
    } catch (error) {
      toast.error('Failed to load advertising data');
    } finally {
      setLoading(false);
    }
  };

  const totalAdSpend = campaigns.reduce((sum, c) => sum + c.ad_spend, 0);
  const totalAdSales = campaigns.reduce((sum, c) => sum + c.ad_sales, 0);
  const avgRoas = totalAdSpend > 0 ? (totalAdSales / totalAdSpend).toFixed(2) : 0;
  const avgAcos = totalAdSales > 0 ? ((totalAdSpend / totalAdSales) * 100).toFixed(2) : 0;

  const COLORS = ['#4338ca', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6'];

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="ad-spend-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Total Ad Spend</p>
                <p className="text-2xl font-bold text-slate-900 font-mono tracking-tight">${totalAdSpend.toLocaleString()}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-rose-50 text-rose-600 flex items-center justify-center">
                <DollarSign size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="ad-sales-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Total Ad Sales</p>
                <p className="text-2xl font-bold text-slate-900 font-mono tracking-tight">${totalAdSales.toLocaleString()}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <TrendingUp size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="roas-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Average ROAS</p>
                <p className="text-2xl font-bold text-slate-900 font-mono tracking-tight">{avgRoas}x</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Target size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="acos-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Average ACOS</p>
                <p className="text-2xl font-bold text-slate-900 font-mono tracking-tight">{avgAcos}%</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-amber-50 text-amber-600 flex items-center justify-center">
                <MousePointer size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Campaign Performance */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="campaign-performance-card">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Campaign Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">Campaign Name</th>
                  <th className="py-3 px-4 text-left">Type</th>
                  <th className="py-3 px-4 text-right">Ad Spend</th>
                  <th className="py-3 px-4 text-right">Ad Sales</th>
                  <th className="py-3 px-4 text-right">ROAS</th>
                  <th className="py-3 px-4 text-right">ACOS</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => (
                  <tr key={campaign.id} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{campaign.campaign_name}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 capitalize">{campaign.campaign_type.replace('_', ' ')}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${campaign.ad_spend.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${campaign.ad_sales.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono">{campaign.roas.toFixed(2)}x</td>
                    <td className="py-3 px-4 text-sm text-indigo-600 text-right font-mono">{campaign.acos.toFixed(2)}%</td>
                    <td className="py-3 px-4 text-center">
                      <Badge className={`${
                        campaign.status === 'active' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-slate-50 text-slate-600 border-slate-200'
                      } rounded-sm text-xs uppercase tracking-wider font-bold`}>
                        {campaign.status}
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

export default Advertising;
