
'use client';

import { useState } from 'react';
import type { BusinessModel as BusinessModelType } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { DollarSign, Layers, Users, ShoppingBag, Info, Zap } from 'lucide-react';
import { Badge } from './ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

const MetricCard = ({ title, value, icon, tooltip }: { title: string, value?: string, icon: React.ReactNode, tooltip?: string }) => {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {tooltip ? (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="cursor-help">{icon}</span>
              </TooltipTrigger>
              <TooltipContent>
                <p>{tooltip}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : (
          icon
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold font-headline">{value || 'N/A'}</div>
        {tooltip && value && value.includes('(') && <p className="text-xs text-muted-foreground pt-1">See tooltip for details</p>}
      </CardContent>
    </Card>
  );
};


export default function BusinessModel({ data, dealId }: { data: BusinessModelType[], dealId: string }) {

  return (
    <div className="space-y-8">
      {data.map((model, index) => (
        <Card key={index}>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="font-headline text-2xl flex items-center gap-3">
                  <DollarSign className="w-7 h-7 text-primary" />
                  {model.revenue_streams}
                </CardTitle>
                <CardDescription>{model.description}</CardDescription>
              </div>
              <Badge>{model.percentage_contribution} Contribution</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h3 className="font-headline text-lg flex items-center gap-2"><Users className="w-5 h-5 text-muted-foreground" />Target Audience</h3>
                <p className="text-sm text-muted-foreground">{model.target_audience}</p>
              </div>
              <div className="space-y-3">
                <h3 className="font-headline text-lg flex items-center gap-2"><ShoppingBag className="w-5 h-5 text-muted-foreground" />Pricing</h3>
                <p className="text-sm text-muted-foreground">{model.pricing}</p>
              </div>
            </div>
            <div>
              <h3 className="font-headline text-xl mb-4">Unit Economics</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                <MetricCard
                  title="LTV"
                  value={model.unit_economics.lifetime_value_LTV}
                  icon={<Info className="h-4 w-4 text-muted-foreground" />}
                  tooltip={model.unit_economics.lifetime_value_LTV}
                />
                <MetricCard
                  title="CAC"
                  value={model.unit_economics.customer_acquisition_cost_CAC}
                  icon={<Info className="h-4 w-4 text-muted-foreground" />}
                  tooltip={model.unit_economics.customer_acquisition_cost_CAC}
                />
                <MetricCard
                  title="LTV/CAC Ratio"
                  value={model.unit_economics.LTV_CAC_Ratio}
                  icon={<Info className="h-4 w-4 text-muted-foreground" />}
                  tooltip={model.unit_economics.LTV_CAC_Ratio}
                />
              </div>
            </div>
            {model.additional_revenue_opportunities && model.additional_revenue_opportunities.length > 0 && (
              <div>
                <h3 className="font-headline text-xl mb-4 flex items-center gap-3"><Zap className="w-6 h-6 text-muted-foreground" />Additional Revenue Opportunities</h3>
                <ul className="list-disc pl-5 text-muted-foreground space-y-1">
                  {model.additional_revenue_opportunities.map((opportunity, i) => (
                    <li key={i}>{opportunity}</li>
                  ))}
                </ul>
              </div>
            )}
            {model.scalability && (
              <div>
                <h3 className="font-headline text-xl mb-4 flex items-center gap-3"><Layers className="w-6 h-6 text-muted-foreground" />Scalability</h3>
                <p className="text-muted-foreground">{model.scalability}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
