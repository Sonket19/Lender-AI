'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { TrendingUp, AlertTriangle, CheckCircle2, DollarSign, Calendar, Target, Flag } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';

type FundingTranche = {
    tranche_number: number;
    amount: string;
    percentage: number;
    timing: string;
    conditions: string[];
};

type Milestone = {
    title: string;
    description: string;
    timeline: string;
    success_criteria: string;
    priority: string;
};

type MilestoneCategory = {
    category: string;
    milestones: Milestone[];
    overall_timeline: string;
};

type InvestmentDecisionData = {
    recommendation: string;
    funding_amount_recommended: string;
    funding_amount_requested: string;
    rationale: string;
    disbursement_schedule: FundingTranche[];
    milestone_roadmap: MilestoneCategory[];
    next_round_criteria: string[];
    red_flags: string[];
    success_metrics: Record<string, string>;
    generated_at?: string;
};

type InvestmentDecisionProps = {
    data: InvestmentDecisionData;
};

const getRecommendationColor = (recommendation: string) => {
    switch (recommendation.toUpperCase()) {
        case 'PROCEED':
            return 'bg-green-500 hover:bg-green-600';
        case 'PASS':
            return 'bg-red-500 hover:bg-red-600';
        case 'CONDITIONAL':
        case 'CONDITIONAL INVEST':
            return 'bg-yellow-500 hover:bg-yellow-600';
        default:
            return 'bg-gray-500 hover:bg-gray-600';
    }
};

const getPriorityColor = (priority: string) => {
    switch (priority.toUpperCase()) {
        case 'HIGH':
            return 'destructive';
        case 'MEDIUM':
            return 'default';
        case 'LOW':
            return 'secondary';
        default:
            return 'outline';
    }
};

export default function InvestmentDecision({ data }: InvestmentDecisionProps) {
    return (
        <div className="space-y-6 animate-in fade-in-50 duration-500">
            <Card className="border-primary/20 shadow-lg">
                <CardHeader>
                    <div className="flex items-start justify-between">
                        <div className="space-y-2">
                            <CardTitle className="text-3xl font-headline flex items-center gap-3">
                                Investment Decision
                                <Badge className={`${getRecommendationColor(data.recommendation)} text-white text-lg px-4 py-1`}>
                                    {data.recommendation.toUpperCase()}
                                </Badge>
                            </CardTitle>
                            <CardDescription className="text-base">
                                Comprehensive funding recommendation and execution plan
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="grid md:grid-cols-2 gap-6">
                        <div className="p-4 bg-secondary/30 rounded-lg border">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                <DollarSign className="h-4 w-4" />
                                <span>Requested Amount</span>
                            </div>
                            <div className="text-2xl font-bold">{data.funding_amount_requested}</div>
                        </div>
                        <div className="p-4 bg-primary/10 rounded-lg border border-primary/30">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                                <TrendingUp className="h-4 w-4" />
                                <span>Recommended Amount</span>
                            </div>
                            <div className="text-2xl font-bold text-primary">{data.funding_amount_recommended}</div>
                        </div>
                    </div>
                    <Accordion type="single" collapsible defaultValue="rationale">
                        <AccordionItem value="rationale">
                            <AccordionTrigger className="text-lg font-semibold">Investment Rationale</AccordionTrigger>
                            <AccordionContent>
                                <div className="prose prose-sm max-w-none text-muted-foreground whitespace-pre-wrap">{data.rationale}</div>
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Calendar className="h-5 w-5" />Disbursement Schedule</CardTitle>
                    <CardDescription>Timeline-based funding tranches with milestone conditions</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {data.disbursement_schedule.map((tranche, index) => (
                            <div key={index} className="relative">
                                {index < data.disbursement_schedule.length - 1 && <div className="absolute left-6 top-14 bottom-0 w-0.5 bg-border" />}
                                <div className="flex gap-4">
                                    <div className="flex-shrink-0 w-12 h-12 rounded-full bg-primary/10 border-2 border-primary flex items-center justify-center font-bold text-primary z-10">{tranche.tranche_number}</div>
                                    <div className="flex-1 pb-8">
                                        <div className="flex items-center justify-between mb-2">
                                            <h4 className="font-semibold text-lg">{tranche.amount}</h4>
                                            <Badge variant="outline">{tranche.percentage}%</Badge>
                                        </div>
                                        <p className="text-sm text-muted-foreground mb-3"><Calendar className="inline h-3 w-3 mr-1" />{tranche.timing}</p>
                                        <div className="space-y-1">
                                            <p className="text-sm font-medium">Conditions:</p>
                                            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                                                {tranche.conditions.map((condition, idx) => <li key={idx}>{condition}</li>)}
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Target className="h-5 w-5" />Milestone Roadmap</CardTitle>
                    <CardDescription>Key achievements required for funding tranches and next round</CardDescription>
                </CardHeader>
                <CardContent>
                    <Accordion type="multiple" className="w-full">
                        {data.milestone_roadmap.map((category, catIndex) => (
                            <AccordionItem key={catIndex} value={`category-${catIndex}`}>
                                <AccordionTrigger className="text-base font-semibold">
                                    <div className="flex items-center justify-between w-full pr-4">
                                        <span>{category.category}</span>
                                        <Badge variant="outline" className="text-xs">{category.overall_timeline}</Badge>
                                    </div>
                                </AccordionTrigger>
                                <AccordionContent>
                                    <div className="space-y-4 pt-2">
                                        {category.milestones.map((milestone, milIndex) => (
                                            <div key={milIndex} className="p-4 bg-secondary/20 rounded-lg border">
                                                <div className="flex items-start justify-between mb-2">
                                                    <h5 className="font-semibold">{milestone.title}</h5>
                                                    <Badge variant={getPriorityColor(milestone.priority)}>{milestone.priority}</Badge>
                                                </div>
                                                <p className="text-sm text-muted-foreground mb-2">{milestone.description}</p>
                                                <div className="grid grid-cols-2 gap-4 text-sm">
                                                    <div><span className="font-medium text-muted-foreground">Timeline: </span><span>{milestone.timeline}</span></div>
                                                    <div><span className="font-medium text-muted-foreground">Success Criteria: </span><span>{milestone.success_criteria}</span></div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </AccordionContent>
                            </AccordionItem>
                        ))}
                    </Accordion>
                </CardContent>
            </Card>

            <div className="grid md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-green-600"><CheckCircle2 className="h-5 w-5" />Next Round Criteria</CardTitle>
                        <CardDescription>Requirements for Series A/B consideration</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-3">
                            {data.next_round_criteria.map((criterion, index) => (
                                <li key={index} className="flex items-start gap-2">
                                    <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 flex-shrink-0" />
                                    <span className="text-sm">{criterion}</span>
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-red-600"><Flag className="h-5 w-5" />Red Flags to Monitor</CardTitle>
                        <CardDescription>Warning signs that could trigger concern</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-3">
                            {data.red_flags.map((flag, index) => (
                                <li key={index} className="flex items-start gap-2">
                                    <AlertTriangle className="h-4 w-4 mt-0.5 text-red-600 flex-shrink-0" />
                                    <span className="text-sm">{flag}</span>
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5" />Success Metrics to Track</CardTitle>
                    <CardDescription>Key performance indicators for ongoing monitoring</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid md:grid-cols-2 gap-4">
                        {Object.entries(data.success_metrics).map(([metric, target], index) => (
                            <div key={index} className="p-4 bg-secondary/20 rounded-lg border">
                                <h5 className="font-semibold mb-1">{metric}</h5>
                                <p className="text-sm text-muted-foreground">{target}</p>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
