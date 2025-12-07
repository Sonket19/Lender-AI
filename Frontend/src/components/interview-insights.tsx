
'use client';

import type { InterviewInsights as InterviewInsightsType } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { MessageSquareQuote, CheckCircle } from 'lucide-react';

const formatInsightKey = (key: string) => {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/\b\w/g, char => char.toUpperCase())
    .replace('Ltv', 'LTV')
    .replace('Cac', 'CAC')
    .replace('Sam', 'SAM')
    .replace('Arr', 'ARR')
    .replace('Mrr', 'MRR');
};

export default function InterviewInsights({ insights }: { insights: InterviewInsightsType }) {
  const insightEntries = Object.entries(insights).filter(([, value]) => value);

  if (insightEntries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="font-headline text-2xl flex items-center gap-3">
            <MessageSquareQuote className="w-7 h-7 text-primary" />
            Interview Insights
          </CardTitle>
          <CardDescription>
            No specific insights were generated from the interview data.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-headline text-2xl flex items-center gap-3">
          <MessageSquareQuote className="w-7 h-7 text-primary" />
          Interview Insights
        </CardTitle>
        <CardDescription>
          The following insights were gathered or clarified during the founder interview.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {insightEntries.map(([key, value]) => (
          <div key={key} className="space-y-2">
            <h3 className="font-headline text-lg flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              {formatInsightKey(key)}
            </h3>
            <p className="text-muted-foreground border-l-2 border-primary pl-4">{value}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
