import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '@/utils/api';
import { Download, Search, Filter } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await apiClient.get('/orders');
      setOrders(response.data.orders);
    } catch (error) {
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  const filteredOrders = orders.filter(order => 
    order.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    order.order_number.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Filters */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
        <CardContent className="p-5">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <Input
                  placeholder="Search orders..."
                  data-testid="search-orders-input"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 border-slate-200 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 rounded-sm bg-white"
                />
              </div>
            </div>
            <Select>
              <SelectTrigger className="w-full md:w-48" data-testid="marketplace-filter">
                <SelectValue placeholder="All Marketplaces" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Marketplaces</SelectItem>
                <SelectItem value="amazon">Amazon</SelectItem>
              </SelectContent>
            </Select>
            <Button data-testid="export-orders-button" className="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-sm font-medium">
              <Download size={16} className="mr-2" />
              Export
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Orders Table */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm">
        <CardHeader>
          <CardTitle className="text-lg font-semibold" style={{ fontFamily: 'Chivo, sans-serif' }}>All Orders ({filteredOrders.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">Order Number</th>
                  <th className="py-3 px-4 text-left">Product</th>
                  <th className="py-3 px-4 text-center">Quantity</th>
                  <th className="py-3 px-4 text-right">Revenue</th>
                  <th className="py-3 px-4 text-left">Marketplace</th>
                  <th className="py-3 px-4 text-left">Date</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4 text-sm text-slate-700 font-mono">{order.order_number}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{order.product_name}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-center font-mono">{order.quantity}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">${order.revenue.toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{order.marketplace}</td>
                    <td className="py-3 px-4 text-sm text-slate-700">{new Date(order.order_date).toLocaleDateString()}</td>
                    <td className="py-3 px-4 text-center">
                      <Badge className={`${
                        order.status === 'delivered' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' :
                        order.status === 'shipped' ? 'bg-indigo-50 text-indigo-600 border-indigo-200' :
                        'bg-amber-50 text-amber-600 border-amber-200'
                      } rounded-sm text-xs uppercase tracking-wider font-bold`}>
                        {order.status}
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

export default Orders;
