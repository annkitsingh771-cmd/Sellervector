import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, Crown } from 'lucide-react';
import { toast } from 'sonner';

const Subscription = () => {
  const plans = [
    {
      name: "Free",
      price: 0,
      period: "forever",
      features: [
        "1 Marketplace",
        "Basic Analytics",
        "10 Products",
        "Email Support"
      ]
    },
    {
      name: "Starter",
      price: 29,
      period: "month",
      popular: false,
      features: [
        "2 Marketplaces",
        "Advanced Analytics",
        "50 Products",
        "Campaign Automation",
        "Priority Support"
      ]
    },
    {
      name: "Professional",
      price: 79,
      period: "month",
      popular: true,
      features: [
        "5 Marketplaces",
        "Full Analytics Suite",
        "Unlimited Products",
        "AI Copilot",
        "FBA Shipment Planner",
        "Inventory Ledger",
        "24/7 Support"
      ]
    },
    {
      name: "Enterprise",
      price: 199,
      period: "month",
      features: [
        "Unlimited Marketplaces",
        "Custom Reports",
        "Unlimited Products",
        "Advanced AI Features",
        "API Access",
        "Dedicated Account Manager",
        "Custom Integrations"
      ]
    }
  ];

  const handleSubscribe = (planName) => {
    toast.success(`Subscription to ${planName} plan initiated! (Demo)`);
  };

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>Choose Your Plan</h2>
        <p className="text-slate-600">Unlock powerful features to grow your e-commerce business</p>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {plans.map((plan, idx) => (
          <Card
            key={idx}
            className={`relative bg-white border ${
              plan.popular ? 'border-indigo-700 shadow-lg' : 'border-slate-200'
            } shadow-sm rounded-sm hover:border-indigo-300 transition-all duration-200`}
            data-testid={`plan-card-${plan.name.toLowerCase()}`}
          >
            {plan.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge className="bg-indigo-700 text-white rounded-sm px-3 py-1 flex items-center gap-1">
                  <Crown size={12} />
                  Most Popular
                </Badge>
              </div>
            )}
            
            <CardHeader className="text-center pb-4">
              <CardTitle className="text-xl mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>{plan.name}</CardTitle>
              <div className="mb-4">
                <span className="text-4xl font-bold text-slate-900 font-mono">${plan.price}</span>
                <span className="text-slate-600">/{plan.period}</span>
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              <ul className="space-y-3 mb-6">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <Check size={16} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              
              <Button
                onClick={() => handleSubscribe(plan.name)}
                data-testid={`subscribe-${plan.name.toLowerCase()}-button`}
                className={`w-full rounded-sm font-medium transition-all duration-150 active:scale-95 ${
                  plan.popular
                    ? 'bg-indigo-700 hover:bg-indigo-800 text-white'
                    : 'bg-white border border-slate-200 hover:bg-slate-50 text-slate-700'
                }`}
              >
                {plan.price === 0 ? 'Current Plan' : 'Upgrade Now'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Compare Features */}
      <Card className="bg-white border border-slate-200 shadow-sm rounded-sm mt-12">
        <CardHeader>
          <CardTitle className="text-xl" style={{ fontFamily: 'Chivo, sans-serif' }}>Why SellerVector?</CardTitle>
          <CardDescription>Advanced features comparable to Helium 10 and Jungle Scout</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <h4 className="font-semibold text-slate-900 mb-2">AI-Powered Insights</h4>
              <p className="text-sm text-slate-600">Get intelligent recommendations to optimize your campaigns and maximize profits</p>
            </div>
            <div>
              <h4 className="font-semibold text-slate-900 mb-2">Automated FBA Management</h4>
              <p className="text-sm text-slate-600">Create bulk shipments with FC codes automatically - no manual work needed</p>
            </div>
            <div>
              <h4 className="font-semibold text-slate-900 mb-2">Real Profit Tracking</h4>
              <p className="text-sm text-slate-600">Calculate true profits including all Amazon fees, GST, and hidden costs</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Subscription;
