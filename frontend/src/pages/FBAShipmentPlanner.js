import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiClient } from '@/utils/api';
import { Package, Download, FileSpreadsheet } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

const FBAShipmentPlanner = () => {
  const [shipments, setShipments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedItems, setSelectedItems] = useState([]);

  useEffect(() => {
    fetchShipments();
  }, []);

  const fetchShipments = async () => {
    try {
      const response = await apiClient.get('/fba/shipment-planner');
      setShipments(response.data.shipments);
    } catch (error) {
      toast.error('Failed to load shipment data');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = () => {
    if (selectedItems.length === shipments.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(shipments.map(s => s.id));
    }
  };

  const handleDownloadBulkSheet = async () => {
    if (selectedItems.length === 0) {
      toast.error('Please select at least one item');
      return;
    }

    try {
      const response = await apiClient.post('/fba/download-bulk-sheet', selectedItems, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'amazon_bulk_shipment.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Bulk shipment sheet downloaded!');
    } catch (error) {
      toast.error('Failed to download sheet');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p>Loading...</p></div>;
  }

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Chivo, sans-serif' }}>FBA Shipment Planner</h2>
          <p className="text-slate-600 text-sm mt-1">Plan and create bulk shipments to Amazon fulfillment centers</p>
        </div>
        <Button
          onClick={handleDownloadBulkSheet}
          disabled={selectedItems.length === 0}
          data-testid="download-bulk-sheet-button"
          className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm font-medium transition-all duration-150 active:scale-95"
        >
          <FileSpreadsheet size={16} className="mr-2" />
          Download Bulk Sheet ({selectedItems.length})
        </Button>
      </div>

      {/* Info Card */}
      <Card className="bg-indigo-50 border border-indigo-200 shadow-sm rounded-sm">
        <CardContent className="p-5">
          <div className="flex items-start gap-3">
            <Package size={20} className="text-indigo-700 mt-0.5" />
            <div>
              <h4 className="font-semibold text-indigo-900 mb-1">Automated FBA Shipment Creation</h4>
              <p className="text-sm text-indigo-700">
                Select products below, download the ready-to-upload CSV file, and upload directly to Amazon Seller Central. No manual editing required!
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Shipments Table */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm" data-testid="shipments-table">
        <CardContent className="p-5">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 text-left">
                    <input
                      type="checkbox"
                      checked={selectedItems.length === shipments.length}
                      onChange={handleSelectAll}
                      data-testid="select-all-checkbox"
                      className="rounded border-slate-300"
                    />
                  </th>
                  <th className="py-3 px-4 text-left">SKU</th>
                  <th className="py-3 px-4 text-left">FNSKU</th>
                  <th className="py-3 px-4 text-left">Product</th>
                  <th className="py-3 px-4 text-right">Current Stock</th>
                  <th className="py-3 px-4 text-right">Qty Needed</th>
                  <th className="py-3 px-4 text-left">FC Code</th>
                  <th className="py-3 px-4 text-center">Priority</th>
                </tr>
              </thead>
              <tbody>
                {shipments.map((shipment) => (
                  <tr key={shipment.id} className="hover:bg-slate-50/50 transition-colors border-b border-slate-100 last:border-0">
                    <td className="py-3 px-4">
                      <input
                        type="checkbox"
                        checked={selectedItems.includes(shipment.id)}
                        onChange={() => {
                          if (selectedItems.includes(shipment.id)) {
                            setSelectedItems(selectedItems.filter(id => id !== shipment.id));
                          } else {
                            setSelectedItems([...selectedItems, shipment.id]);
                          }
                        }}
                        className="rounded border-slate-300"
                      />
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700 font-mono">{shipment.sku}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 font-mono">{shipment.fnsku}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 font-medium">{shipment.title}</td>
                    <td className="py-3 px-4 text-sm text-slate-700 text-right font-mono">{shipment.current_stock}</td>
                    <td className="py-3 px-4 text-sm text-emerald-600 text-right font-mono font-bold">{shipment.quantity_needed}</td>
                    <td className="py-3 px-4 text-sm text-indigo-700 font-mono font-bold">{shipment.fc_code}</td>
                    <td className="py-3 px-4 text-center">
                      <Badge className={`${
                        shipment.priority === 'high' ? 'bg-rose-50 text-rose-600 border-rose-200' : 'bg-amber-50 text-amber-600 border-amber-200'
                      } rounded-sm text-xs uppercase tracking-wider font-bold`}>
                        {shipment.priority}
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

export default FBAShipmentPlanner;
