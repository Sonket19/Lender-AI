'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CheckCircle2, XCircle, AlertCircle, Shield, Building2, Calculator, Gavel, FileCheck } from 'lucide-react';

// Types for Credit Analysis
interface GateCheck {
    name: string;
    status: string;
    result: string;
    details: string;
    flags?: string[];
}

interface Gate {
    gate_number: number;
    gate_name: string;
    status: string;
    checks: GateCheck[];
}

interface SummaryTableEntry {
    parameter: string;
    result: string;
    status: string;
}

interface CreditAnalysisData {
    gates: Gate[];
    loan_amount_requested: string;
    max_permissible_limit: string;
    dscr: string;
    current_ratio: string;
    tol_tnw_ratio: string;
    runway_months: string;
    recommendation: string;
    sanction_amount: string;
    conditions: string[];
    rejection_reasons: string[];
    cgtmse_eligible: boolean;
    summary_table: SummaryTableEntry[];
    final_verdict: string;
}

interface CreditAnalysisProps {
    data: CreditAnalysisData | null | undefined;
}

const getStatusIcon = (status: string) => {
    const statusLower = status?.toLowerCase() || '';
    if (statusLower.includes('pass') || statusLower.includes('🟢')) {
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    } else if (statusLower.includes('fail') || statusLower.includes('reject') || statusLower.includes('🔴')) {
        return <XCircle className="w-5 h-5 text-red-500" />;
    } else {
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
    }
};

const getStatusBadge = (status: string) => {
    const statusLower = status?.toLowerCase() || '';
    if (statusLower.includes('pass') || statusLower.includes('🟢')) {
        return <Badge className="bg-green-100 text-green-800 border-green-300">Pass</Badge>;
    } else if (statusLower.includes('fail') || statusLower.includes('reject') || statusLower.includes('🔴')) {
        return <Badge className="bg-red-100 text-red-800 border-red-300">Fail</Badge>;
    } else {
        return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300">Review</Badge>;
    }
};

const getGateIcon = (gateNumber: number) => {
    switch (gateNumber) {
        case 1: return <Shield className="w-5 h-5" />;
        case 2: return <FileCheck className="w-5 h-5" />;
        case 3: return <Calculator className="w-5 h-5" />;
        case 4: return <Gavel className="w-5 h-5" />;
        default: return <Building2 className="w-5 h-5" />;
    }
};

const RecommendationCard = ({ data }: { data: CreditAnalysisData }) => {
    const isApproved = data.recommendation?.toLowerCase().includes('sanction');
    const isRejected = data.recommendation?.toLowerCase().includes('reject');

    return (
        <Card className={`border-2 ${isApproved ? 'border-green-500 bg-green-50/50' : isRejected ? 'border-red-500 bg-red-50/50' : 'border-yellow-500 bg-yellow-50/50'}`}>
            <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-xl">
                    {isApproved ? (
                        <CheckCircle2 className="w-6 h-6 text-green-600" />
                    ) : isRejected ? (
                        <XCircle className="w-6 h-6 text-red-600" />
                    ) : (
                        <AlertCircle className="w-6 h-6 text-yellow-600" />
                    )}
                    Credit Decision: {data.recommendation}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-white/80 rounded-lg">
                        <div className="text-sm text-muted-foreground">Requested</div>
                        <div className="text-lg font-bold">{data.loan_amount_requested || 'N/A'}</div>
                    </div>
                    <div className="text-center p-3 bg-white/80 rounded-lg">
                        <div className="text-sm text-muted-foreground">MPBF Limit</div>
                        <div className="text-lg font-bold text-primary">{data.max_permissible_limit || 'N/A'}</div>
                    </div>
                    <div className="text-center p-3 bg-white/80 rounded-lg">
                        <div className="text-sm text-muted-foreground">Sanctioned</div>
                        <div className="text-lg font-bold text-green-600">{data.sanction_amount || 'N/A'}</div>
                    </div>
                    <div className="text-center p-3 bg-white/80 rounded-lg">
                        <div className="text-sm text-muted-foreground">CGTMSE</div>
                        <div className="text-lg font-bold">{data.cgtmse_eligible ? '✅ Eligible' : '❌ Not Eligible'}</div>
                    </div>
                </div>

                <div className="p-4 bg-white/80 rounded-lg">
                    <h4 className="font-semibold mb-2">Final Verdict</h4>
                    <p className="text-sm">{data.final_verdict || 'No verdict available'}</p>
                </div>

                {data.conditions && data.conditions.length > 0 && (
                    <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                        <h4 className="font-semibold mb-2 text-yellow-800">Conditions</h4>
                        <ul className="list-disc list-inside text-sm text-yellow-700">
                            {data.conditions.map((condition, idx) => (
                                <li key={idx}>{condition}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {data.rejection_reasons && data.rejection_reasons.length > 0 && data.rejection_reasons[0] && (
                    <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                        <h4 className="font-semibold mb-2 text-red-800">Rejection Reasons</h4>
                        <ul className="list-disc list-inside text-sm text-red-700">
                            {data.rejection_reasons.map((reason, idx) => (
                                <li key={idx}>{reason}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

const SummaryTable = ({ entries }: { entries: SummaryTableEntry[] }) => {
    if (!entries || entries.length === 0) return null;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Credit Assessment Summary</CardTitle>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Parameter</TableHead>
                            <TableHead>Result</TableHead>
                            <TableHead className="text-center">Status</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {entries.map((entry, idx) => (
                            <TableRow key={idx}>
                                <TableCell className="font-medium">{entry.parameter}</TableCell>
                                <TableCell>{entry.result}</TableCell>
                                <TableCell className="text-center">
                                    <span className="flex items-center justify-center gap-2">
                                        {getStatusIcon(entry.status)}
                                        <span className="text-sm">{entry.status.replace(/🟢|🟡|🔴/g, '').trim()}</span>
                                    </span>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    );
};

const KeyMetrics = ({ data }: { data: CreditAnalysisData }) => (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
            <CardContent className="pt-4 text-center">
                <div className="text-sm text-muted-foreground">DSCR</div>
                <div className="text-2xl font-bold">{data.dscr || 'N/A'}</div>
                <div className="text-xs text-muted-foreground">Debt Service Coverage</div>
            </CardContent>
        </Card>
        <Card>
            <CardContent className="pt-4 text-center">
                <div className="text-sm text-muted-foreground">Current Ratio</div>
                <div className="text-2xl font-bold">{data.current_ratio || 'N/A'}</div>
                <div className="text-xs text-muted-foreground">Liquidity</div>
            </CardContent>
        </Card>
        <Card>
            <CardContent className="pt-4 text-center">
                <div className="text-sm text-muted-foreground">TOL/TNW</div>
                <div className="text-2xl font-bold">{data.tol_tnw_ratio || 'N/A'}</div>
                <div className="text-xs text-muted-foreground">Leverage</div>
            </CardContent>
        </Card>
        <Card>
            <CardContent className="pt-4 text-center">
                <div className="text-sm text-muted-foreground">Runway</div>
                <div className="text-2xl font-bold">{data.runway_months || 'N/A'}</div>
                <div className="text-xs text-muted-foreground">Post-Loan</div>
            </CardContent>
        </Card>
    </div>
);

const GateAccordion = ({ gates }: { gates: Gate[] }) => {
    if (!gates || gates.length === 0) return null;

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">4-Gate Credit Analysis</CardTitle>
            </CardHeader>
            <CardContent>
                <Accordion type="multiple" className="w-full">
                    {gates.map((gate) => (
                        <AccordionItem key={gate.gate_number} value={`gate-${gate.gate_number}`}>
                            <AccordionTrigger className="hover:no-underline">
                                <div className="flex items-center gap-3 w-full">
                                    <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary">
                                        {getGateIcon(gate.gate_number)}
                                    </span>
                                    <span className="flex-1 text-left">
                                        Gate {gate.gate_number}: {gate.gate_name}
                                    </span>
                                    {getStatusBadge(gate.status)}
                                </div>
                            </AccordionTrigger>
                            <AccordionContent>
                                <div className="space-y-3 pt-2">
                                    {gate.checks?.map((check, idx) => (
                                        <div key={idx} className="p-3 bg-secondary/30 rounded-lg">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="font-medium flex items-center gap-2">
                                                    {getStatusIcon(check.status)}
                                                    {check.name}
                                                </span>
                                                {getStatusBadge(check.status)}
                                            </div>
                                            <div className="text-sm space-y-1">
                                                <p><span className="text-muted-foreground">Result:</span> {check.result}</p>
                                                <p><span className="text-muted-foreground">Details:</span> {check.details}</p>
                                                {check.flags && check.flags.length > 0 && (
                                                    <div className="flex flex-wrap gap-1 mt-2">
                                                        {check.flags.map((flag, flagIdx) => (
                                                            <Badge key={flagIdx} variant="destructive" className="text-xs">
                                                                🚩 {flag}
                                                            </Badge>
                                                        ))}
                                                    </div>
                                                )}
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
    );
};

export default function CreditAnalysis({ data }: CreditAnalysisProps) {
    if (!data) {
        return (
            <Card>
                <CardContent className="py-8">
                    <div className="text-center text-muted-foreground">
                        <Calculator className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No credit analysis available</p>
                        <p className="text-sm mt-2">Credit analysis will appear once the deal is processed</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            <RecommendationCard data={data} />
            <KeyMetrics data={data} />
            <SummaryTable entries={data.summary_table} />
            <GateAccordion gates={data.gates} />
        </div>
    );
}
