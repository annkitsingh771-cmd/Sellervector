import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/utils/api';
import { Users, TrendingDown, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';

const Competitors = () => {
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCompetitors();
  }, []);

  const fetchCompetitors = async () => {
    try {
      const response = await apiClient.get('/competitors');
      setCompetitors(response.data.competitors);
    } catch (error) {
      toast.error('Failed to load competitor data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <Card className="bg-indigo-50 border border-indigo-200 shadow-sm rounded-sm">
        <CardContent className="p-5">
          <div className="flex items-start gap-3">
            <Users size={20} className="text-indigo-700 mt-0.5" />
            <div>
              <h4 className="font-semibold text-indigo-900 mb-1">Competitor Monitoring</h4>
              <p className="text-sm text-indigo-700">
                Track competitor prices, ratings, and advertising activity to stay competitive in the marketplace.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Competitors Table */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="competitors-table">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Competitor Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">Competitor</th>
                  <th className="py-3 px-4 text-right">Their Price</th>
                  <th className="py-3 px-4 text-right">Your Price</th>
                  <th className="py-3 px-4 text-right">Difference</th>
                  <th className="py-3 px-4 text-right">Reviews</th>
                  <th className="py-3 px-4 text-right">Rating</th>
                  <th className="py-3 px-4 text-left">Marketplace</th>
                </tr>
              </thead>
              <tbody>
                {competitors.map((comp) => (
                  <tr key={comp.id} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{comp.competitor_name}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${comp.competitor_price.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${comp.your_price.toFixed(2)}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {comp.price_difference < 0 ? (
                          <TrendingDown size={14} className="text-emerald-600" />
                        ) : (
                          <TrendingUp size={14} className="text-rose-600" />
                        )}
                        <span className={`text-sm font-mono font-semibold ${
                          comp.price_difference < 0 ? 'text-emerald-600' : 'text-rose-600'
                        }`}>
                          ${Math.abs(comp.price_difference).toFixed(2)}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{comp.review_count.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right">
                      <Badge className="bg-amber-50 text-amber-600 border-amber-200 rounded-sm font-mono text-xs">
                        {comp.rating.toFixed(1)} ★
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700">{comp.marketplace}</td>
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

export default Competitors;
