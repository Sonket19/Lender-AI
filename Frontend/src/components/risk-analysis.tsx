
'use client';

import { useState } from 'react';
import type { RiskMetrics, Conclusion, RiskAndMitigation } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { AlertTriangle, ShieldCheck, CheckCircle, Info, SlidersHorizontal, Loader2, ArrowRight } from 'lucide-react';
import { Badge } from './ui/badge';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

const ScoreCircle = ({ score, isLoading }: { score: string | number; isLoading?: boolean }) => {
  const numericScore = typeof score === 'string' ? parseFloat(score) : score;
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (numericScore / 100) * circumference;

  let colorClass = 'text-chart-2';
  if (numericScore < 70) colorClass = 'text-chart-4';
  if (numericScore < 50) colorClass = 'text-chart-1';

  return (
    <div className="relative w-48 h-48">
      <svg className="w-full h-full" viewBox="0 0 100 100">
        <circle
          className="text-secondary"
          strokeWidth="10"
          stroke="currentColor"
          fill="transparent"
          r="45"
          cx="50"
          cy="50"
        />
        {!isLoading && (
          <circle
            className={colorClass}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            stroke="currentColor"
            fill="transparent"
            r="45"
            cx="50"
            cy="50"
            transform="rotate(-90 50 50)"
            style={{ transition: 'stroke-dashoffset 0.5s ease-out' }}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {isLoading ? (
          <Loader2 className="w-12 h-12 animate-spin text-primary" />
        ) : (
          <>
            <span className={`font-headline font-bold text-4xl ${colorClass}`}>{score}%</span>
            <span className="text-sm text-muted-foreground">Safety Score</span>
          </>
        )}
      </div>
    </div>
  );
};


export default function RiskAnalysis({ riskMetrics, conclusion, risksAndMitigation, isRecalculating }: { riskMetrics: RiskMetrics, conclusion: Conclusion, risksAndMitigation: RiskAndMitigation[], isRecalculating: boolean }) {

  const getImpactColor = (impact: string) => {
    switch (impact.toLowerCase()) {
      case 'high': return 'bg-destructive/80';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-gray-400';
    }
  }
  const getLikelihoodColor = (likelihood: string) => {
    switch (likelihood.toLowerCase()) {
      case 'high': return 'bg-destructive/80';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-gray-400';
    }
  }

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <div className="space-y-1.5">
            <CardTitle className="font-headline text-2xl flex items-center gap-3"><ShieldCheck className="w-7 h-7 text-primary" />Risk Metrics</CardTitle>
            <CardDescription>Generated composite score and narrative justification.</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col md:flex-row items-center gap-8">
          <div className="flex-shrink-0">
            <ScoreCircle score={riskMetrics.composite_risk_score} isLoading={isRecalculating} />
          </div>
          <div className="space-y-4">
            <h3 className="font-headline text-xl">Narrative Justification</h3>
            <p className="text-muted-foreground">{riskMetrics.narrative_justification}</p>
            <Badge>{riskMetrics.score_interpretation}</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="font-headline text-2xl flex items-center gap-3"><AlertTriangle className="w-7 h-7 text-primary" />Risks and Mitigations</CardTitle>
          <CardDescription>Detailed analysis of potential risks and suggested mitigation strategies.</CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible className="w-full">
            {risksAndMitigation.map((item, index) => (
              <AccordionItem value={`item-${index}`} key={index}>
                <AccordionTrigger>
                  <div className="flex items-center gap-4 w-full">
                    <span className="font-semibold text-left flex-1">{item.risk}</span>
                    <div className="flex items-center gap-2">
                      <Badge className={getLikelihoodColor(item.likelihood)}>{item.likelihood} Likelihood</Badge>
                      <Badge className={getImpactColor(item.impact)}>{item.impact} Impact</Badge>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-4">
                  <p className="text-muted-foreground">{item.description}</p>
                  <div>
                    <h4 className="font-semibold flex items-center gap-2 mb-2"><ArrowRight className="w-4 h-4 text-primary" />Mitigation</h4>
                    <p className="text-sm text-muted-foreground border-l-2 border-primary pl-4">{item.mitigation}</p>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="font-headline text-2xl flex items-center gap-3"><CheckCircle className="w-7 h-7 text-primary" />Conclusion</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Overall Recommendation</h3>
            <p className="text-muted-foreground mb-4">{conclusion.overall_attractiveness}</p>

            <ul className="space-y-3">
              {conclusion.product_summary && (
                <li className="flex flex-col md:flex-row gap-2">
                  <span className="font-semibold min-w-[160px] text-primary/80">Product:</span>
                  <span className="text-muted-foreground">{conclusion.product_summary}</span>
                </li>
              )}
              {conclusion.financial_analysis && (
                <li className="flex flex-col md:flex-row gap-2">
                  <span className="font-semibold min-w-[160px] text-primary/80">Financials:</span>
                  <span className="text-muted-foreground">{conclusion.financial_analysis}</span>
                </li>
              )}
              {conclusion.investment_thesis && (
                <li className="flex flex-col md:flex-row gap-2">
                  <span className="font-semibold min-w-[160px] text-primary/80">Investment Thesis:</span>
                  <span className="text-muted-foreground">{conclusion.investment_thesis}</span>
                </li>
              )}
              {conclusion.risk_summary && (
                <li className="flex flex-col md:flex-row gap-2">
                  <span className="font-semibold min-w-[160px] text-primary/80">Risk Score:</span>
                  <span className="text-muted-foreground">{conclusion.risk_summary}</span>
                </li>
              )}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
