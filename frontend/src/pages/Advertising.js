import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '@/utils/api';
import { TrendingUp, Target, MousePointer, Eye, DollarSign, Calendar } from 'lucide-react';
import { toast } from 'sonner';

const Advertising = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30');
  const [marketplace, setMarketplace] = useState('all');

  useEffect(() => {
    fetchCampaigns();
  }, [dateRange, marketplace]);

  const fetchCampaigns = async () => {
    try {
      const response = await apiClient.get('/campaigns');
      setCampaigns(response.data.campaigns || []);
    } catch (error) {
      toast.error('Failed to load advertising data');
    } finally {
      setLoading(false);
    }
  };

  const totalAdSpend = campaigns.reduce((sum, c) => sum + (c.ad_spend || 0), 0);
  const totalAdSales = campaigns.reduce((sum, c) => sum + (c.ad_sales || 0), 0);
  const totalImpressions = campaigns.reduce((sum, c) => sum + (c.impressions || 0), 0);
  const totalClicks = campaigns.reduce((sum, c) => sum + (c.clicks || 0), 0);
  const totalOrders = campaigns.reduce((sum, c) => sum + (c.orders || 0), 0);
  
  const avgCTR = totalImpressions > 0 ? (totalClicks / totalImpressions * 100) : 0;
  const avgCVR = totalClicks > 0 ? (totalOrders / totalClicks * 100) : 0;
  const avgCPC = totalClicks > 0 ? (totalAdSpend / totalClicks) : 0;
  const avgRoas = totalAdSpend > 0 ? (totalAdSales / totalAdSpend) : 0;
  const avgAcos = totalAdSales > 0 ? ((totalAdSpend / totalAdSales) * 100) : 0;

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

      {/* Metrics Grid - 8 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-4">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="ad-spend-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Ad Spend</p>
            <p className="text-xl font-bold text-rose-600 font-mono tracking-tight">${totalAdSpend.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="ad-sales-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Ad Sales</p>
            <p className="text-xl font-bold text-emerald-600 font-mono tracking-tight">${totalAdSales.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="impressions-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Impressions</p>
            <p className="text-xl font-bold text-slate-900 font-mono tracking-tight">{totalImpressions.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="clicks-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Clicks</p>
            <p className="text-xl font-bold text-slate-900 font-mono tracking-tight">{totalClicks.toLocaleString()}</p>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="ctr-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">CTR</p>
            <p className="text-xl font-bold text-indigo-600 font-mono tracking-tight">{avgCTR.toFixed(2)}%</p>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="cvr-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">CVR</p>
            <p className="text-xl font-bold text-emerald-600 font-mono tracking-tight">{avgCVR.toFixed(2)}%</p>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="cpc-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Avg CPC</p>
            <p className="text-xl font-bold text-amber-600 font-mono tracking-tight">${avgCPC.toFixed(2)}</p>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="roas-card">
          <CardContent className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">ROAS</p>
            <p className="text-xl font-bold text-emerald-600 font-mono tracking-tight">{avgRoas.toFixed(2)}x</p>
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
                  <th className="py-3 px-4 text-right">Impressions</th>
                  <th className="py-3 px-4 text-right">Clicks</th>
                  <th className="py-3 px-4 text-right">CTR</th>
                  <th className="py-3 px-4 text-right">Orders</th>
                  <th className="py-3 px-4 text-right">CVR</th>
                  <th className="py-3 px-4 text-right">Ad Spend</th>
                  <th className="py-3 px-4 text-right">Ad Sales</th>
                  <th className="py-3 px-4 text-right">CPC</th>
                  <th className="py-3 px-4 text-right">ROAS</th>
                  <th className="py-3 px-4 text-right">ACOS</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => {
                  const cpc = campaign.clicks > 0 ? campaign.ad_spend / campaign.clicks : 0;
                  return (
                    <tr key={campaign.id} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                      <td className="py-3 px-4 text-sm text-slate-700 font-medium">{campaign.campaign_name}</td>
                      <td className="py-3 px-4 text-sm text-slate-700 capitalize">{campaign.campaign_type?.replace('_', ' ')}</td>
                      <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{(campaign.impressions || 0).toLocaleString()}</td>
                      <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{(campaign.clicks || 0).toLocaleString()}</td>
                      <td className="py-3 px-4 text-sm text-indigo-600 text-right font-mono">{(campaign.ctr || 0).toFixed(2)}%</td>
                      <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{campaign.orders || 0}</td>
                      <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono">{(campaign.cvr || 0).toFixed(2)}%</td>
                      <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">${(campaign.ad_spend || 0).toFixed(2)}</td>
                      <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono">${(campaign.ad_sales || 0).toFixed(2)}</td>
                      <td className="py-3 px-4 text-sm text-amber-600 text-right font-mono">${cpc.toFixed(2)}</td>
                      <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono">{(campaign.roas || 0).toFixed(2)}x</td>
                      <td className="py-3 px-4 text-sm text-indigo-600 text-right font-mono">{(campaign.acos || 0).toFixed(2)}%</td>
                      <td className="py-3 px-4 text-center">
                        <Badge className={`${
                          campaign.status === 'active' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-slate-50 text-slate-600 border-slate-200'
                        } rounded-sm text-xs uppercase tracking-wider font-bold`}>
                          {campaign.status}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Advertising;
