import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/utils/api';
import { TrendingUp, Box, DollarSign } from 'lucide-react';
import { toast } from 'sonner';

const Products = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await apiClient.get('/products');
      setProducts(response.data);
    } catch (error) {
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  const totalRevenue = products.reduce((sum, p) => sum + p.revenue, 0);
  const totalProfit = products.reduce((sum, p) => sum + p.profit, 0);

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="total-products-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Total Products</p>
                <p className="text-3xl font-bold text-slate-900 font-mono tracking-tight">{products.length}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <Box size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="products-revenue-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Total Revenue</p>
                <p className="text-3xl font-bold text-emerald-600 font-mono tracking-tight">${totalRevenue.toLocaleString()}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <DollarSign size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="products-profit-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Total Profit</p>
                <p className="text-3xl font-bold text-indigo-600 font-mono tracking-tight">${totalProfit.toLocaleString()}</p>
              </div>
              <div className="w-12 h-12 rounded-sm bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <TrendingUp size={24} strokeWidth={1.5} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Products Table */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="products-table">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>Product Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">Product Name</th>
                  <th className="py-3 px-4 text-left">SKU</th>
                  <th className="py-3 px-4 text-right">Price</th>
                  <th className="py-3 px-4 text-right">Stock</th>
                  <th className="py-3 px-4 text-right">Revenue</th>
                  <th className="py-3 px-4 text-right">Orders</th>
                  <th className="py-3 px-4 text-right">Conv. Rate</th>
                  <th className="py-3 px-4 text-right">Ad Spend</th>
                  <th className="py-3 px-4 text-right">Profit</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{product.name}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 font-mono">{product.sku}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${product.price.toFixed(2)}</td>
                    <td className="py-3 px-4 text-right">
                      <Badge className={`${
                        product.stock_level < 50 ? 'bg-amber-50 text-amber-600 border-amber-200' : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                      } rounded-sm font-mono text-xs`}>
                        {product.stock_level}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${product.revenue.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{product.orders}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{product.conversion_rate.toFixed(2)}%</td>
                    <td className="py-3 px-4 text-sm text-rose-600 text-right font-mono">${product.ad_spend.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono font-bold">${product.profit.toFixed(2)}</td>
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

export default Products;
