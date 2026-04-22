import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { apiClient } from '@/utils/api';
import { TrendingUp, AlertTriangle, FlaskConical, Star } from 'lucide-react';
import { toast } from 'sonner';

const KeywordReport = () => {
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchKeywords();
  }, []);

  const fetchKeywords = async () => {
    try {
      const response = await apiClient.get('/campaigns/wasted-spend');
      setKeywords(response.data.wasted_keywords || []);
    } catch (error) {
      toast.error('Failed to load keyword data');
    } finally {
      setLoading(false);
    }
  };

  // Categorize keywords
  const heroKeywords = keywords.filter(k => k.sales > 500 && k.acos < 20);
  const wastageKeywords = keywords.filter(k => k.sales === 0 && k.spend > 50);
  const testKeywords = keywords.filter(k => k.sales > 0 && k.sales < 200);

  const totalWastage = wastageKeywords.reduce((sum, k) => sum + (k.spend || 0), 0);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="hero-keywords-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Hero Keywords</p>
                <p className="text-3xl font-bold text-emerald-600 font-mono tracking-tight">{heroKeywords.length}</p>
                <p className="text-xs text-slate-500 mt-1">Top performing keywords</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Star size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="wastage-keywords-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Wastage Keywords</p>
                <p className="text-3xl font-bold text-rose-600 font-mono tracking-tight">{wastageKeywords.length}</p>
                <p className="text-xs text-slate-500 mt-1">₹{totalWastage.toFixed(2)} wasted</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-rose-50 text-rose-600 flex items-center justify-center">
                <AlertTriangle size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="test-keywords-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Test Keywords</p>
                <p className="text-3xl font-bold text-amber-600 font-mono tracking-tight">{testKeywords.length}</p>
                <p className="text-xs text-slate-500 mt-1">Need optimization</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-amber-50 text-amber-600 flex items-center justify-center">
                <FlaskConical size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Keyword Tabs */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Keyword Performance Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="wastage" className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6">
              <TabsTrigger value="wastage" data-testid="wastage-tab">
                <AlertTriangle size={16} className="mr-2" />
                Wastage ({wastageKeywords.length})
              </TabsTrigger>
              <TabsTrigger value="hero" data-testid="hero-tab">
                <Star size={16} className="mr-2" />
                Hero ({heroKeywords.length})
              </TabsTrigger>
              <TabsTrigger value="test" data-testid="test-tab">
                <FlaskConical size={16} className="mr-2" />
                Test ({testKeywords.length})
              </TabsTrigger>
            </TabsList>

            {/* Wastage Keywords */}
            <TabsContent value="wastage">
              <div className="bg-rose-50 border border-rose-200 rounded-sm p-4 mb-4">
                <p className="text-sm text-rose-700">
                  <strong>Wastage Keywords:</strong> Keywords with high spend but zero sales. Consider pausing or adding as negative keywords.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                      <th className="py-3 px-4 text-left">Keyword</th>
                      <th className="py-3 px-4 text-left">Campaign</th>
                      <th className="py-3 px-4 text-right">Spend</th>
                      <th className="py-3 px-4 text-right">Clicks</th>
                      <th className="py-3 px-4 text-right">Sales</th>
                      <th className="py-3 px-4 text-left">Action Needed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wastageKeywords.map((keyword, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                        <td className="py-3 px-4 text-sm text-slate-700 font-medium">{keyword.keyword}</td>
                        <td className="py-3 px-4 text-sm text-slate-700">{keyword.campaign_name}</td>
                        <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono font-bold">₹{keyword.spend.toFixed(2)}</td>
                        <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{keyword.clicks}</td>
                        <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">₹{keyword.sales.toFixed(2)}</td>
                        <td className="py-3 px-4 text-sm">
                          <Badge className="bg-rose-50 text-rose-600 border-rose-200 rounded-sm text-xs">
                            {keyword.suggestion}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </TabsContent>

            {/* Hero Keywords */}
            <TabsContent value="hero">
              <div className="bg-emerald-50 border border-emerald-200 rounded-sm p-4 mb-4">
                <p className="text-sm text-emerald-700">
                  <strong>Hero Keywords:</strong> Top performing keywords with high sales and low ACOS. Scale these up for maximum profitability.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                      <th className="py-3 px-4 text-left">Keyword</th>
                      <th className="py-3 px-4 text-left">Campaign</th>
                      <th className="py-3 px-4 text-right">Spend</th>
                      <th className="py-3 px-4 text-right">Sales</th>
                      <th className="py-3 px-4 text-right">ROAS</th>
                      <th className="py-3 px-4 text-right">ACOS</th>
                      <th className="py-3 px-4 text-left">Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {heroKeywords.length === 0 ? (
                      <tr>
                        <td colSpan="7" className="py-8 text-center text-slate-500">
                          No hero keywords found yet. Keep optimizing!
                        </td>
                      </tr>
                    ) : (
                      heroKeywords.map((keyword, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                          <td className="py-3 px-4 text-sm text-slate-700 font-medium">{keyword.keyword}</td>
                          <td className="py-3 px-4 text-sm text-slate-700">{keyword.campaign_name}</td>
                          <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">₹{keyword.spend.toFixed(2)}</td>
                          <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono font-bold">₹{keyword.sales.toFixed(2)}</td>
                          <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono">{keyword.roas}x</td>
                          <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono">{keyword.acos}%</td>
                          <td className="py-3 px-4 text-sm">
                            <Badge className="bg-emerald-50 text-emerald-600 border-emerald-200 rounded-sm text-xs">
                              Increase Budget
                            </Badge>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </TabsContent>

            {/* Test Keywords */}
            <TabsContent value="test">
              <div className="bg-amber-50 border border-amber-200 rounded-sm p-4 mb-4">
                <p className="text-sm text-amber-700">
                  <strong>Test Keywords:</strong> Keywords with moderate performance. Monitor and optimize bid strategies for these.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                      <th className="py-3 px-4 text-left">Keyword</th>
                      <th className="py-3 px-4 text-left">Campaign</th>
                      <th className="py-3 px-4 text-right">Spend</th>
                      <th className="py-3 px-4 text-right">Sales</th>
                      <th className="py-3 px-4 text-right">Orders</th>
                      <th className="py-3 px-4 text-left">Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {testKeywords.length === 0 ? (
                      <tr>
                        <td colSpan="6" className="py-8 text-center text-slate-500">
                          No test keywords found
                        </td>
                      </tr>
                    ) : (
                      testKeywords.map((keyword, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                          <td className="py-3 px-4 text-sm text-slate-700 font-medium">{keyword.keyword}</td>
                          <td className="py-3 px-4 text-sm text-slate-700">{keyword.campaign_name}</td>
                          <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">₹{keyword.spend.toFixed(2)}</td>
                          <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">₹{keyword.sales.toFixed(2)}</td>
                          <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{keyword.orders}</td>
                          <td className="py-3 px-4 text-sm">
                            <Badge className="bg-amber-50 text-amber-600 border-amber-200 rounded-sm text-xs">
                              Monitor & Optimize
                            </Badge>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default KeywordReport;
