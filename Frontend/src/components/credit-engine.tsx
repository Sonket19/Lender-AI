'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { useToast } from '@/hooks/use-toast';
import { authenticatedFetch } from '@/lib/api-client';
import {
    CheckCircle2,
    XCircle,
    AlertCircle,
    TrendingUp,
    Landmark,
    FileSearch,
    ArrowRight,
    ShieldCheck,
    AlertTriangle,
    Banknote,
    Percent,
    ArrowDownRight,
    Activity,
    ChevronDown,
    ChevronUp,
    Info
} from 'lucide-react';
import {
    ResponsiveContainer,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    Tooltip,
    Legend
} from 'recharts';
import { cn } from '@/lib/utils';

// --- Types ---

interface WaterfallStep {
    step_number: number;
    scheme_name: string;
    rule_checked: string;
    result: string;
    reason: string;
}

interface CreditEngineData {
    deal_id: string;
    status: string;
    eligible_scheme: string;
    max_permissible_limit: number;
    recommended_amount: number;
    current_ratio: number;
    current_ratio_status: string;
    tol_tnw: number;
    leverage_status: string;
    avg_dscr: number;
    dscr_status: string;
    credit_score?: number;
    radar_chart_data: Record<string, number>;
    waterfall_data: WaterfallStep[];
    flags: string[];
    rejection_reasons: string[];
    compliance_notes: string[];
    cgtmse_eligible: boolean;
    mudra_eligible: boolean;
    cgss_eligible: boolean;
    working_capital_analysis?: {
        // Common fields
        gross_wc: number;
        margin: number;
        mpbf: number;
        method: string;
        method_used?: string;
        method_code?: 'NAYAK' | 'TANDON' | 'NONE';
        eligible_bank_finance?: number;
        chart_data?: Array<{ label: string; value: number; type: string }>;
        // Nayak-specific
        projected_turnover?: number;
        gross_working_capital_need?: number;
        promoter_contribution_5_percent?: number;
        // Tandon-specific
        total_current_assets?: number;
        other_current_liabilities?: number;
        wc_gap?: number;
        working_capital_gap?: number;
        margin_on_assets_25_percent?: number;
        surplus_liquidity?: boolean;
        conservative_adjustment?: string;
    };
}

interface MemoCreditAnalysis {
    gates?: Array<{
        gate_number: number;
        gate_name: string;
        status: string;
        checks: Array<{
            name: string;
            status: string;
            result: string;
            details: string;
        }>;
    }>;
    loan_amount_requested?: string;
    max_permissible_limit?: string;
    dscr?: string;
    current_ratio?: string;
    tol_tnw_ratio?: string;
    recommendation?: string;
    sanction_amount?: string;
    cgtmse_eligible?: boolean;
    final_verdict?: string;
    summary_table?: Array<{
        parameter: string;
        result: string;
        status: string;
    }>;
    conditions?: string[];
    rejection_reasons?: string[];
}

interface CreditEngineProps {
    data: CreditEngineData | null | undefined;
    memoCreditData?: MemoCreditAnalysis | null;
    dealId?: string;
    loanAmountRequested?: string;
}

// --- Helpers ---

const formatCurrency = (amount: number) => {
    if (!amount && amount !== 0) return '₹0';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(amount);
};

// --- Sub-Components ---

const MetricTile = ({ title, value, status, footer }: any) => {
    const s = status?.toLowerCase() || '';
    const isGood = s.includes('approve') || s.includes('pass') || s.includes('safe') || s.includes('eligible') || s.includes('good') || (!isNaN(parseFloat(status)) && parseFloat(status) > 0);
    // Simplified logic, specific status check below

    // Status Badge Logic
    let badgeClass = "bg-slate-100 text-slate-700";
    if (s.includes('approve') || s.includes('pass') || s.includes('safe') || s.includes('eligible')) badgeClass = "bg-emerald-100 text-emerald-700";
    else if (s.includes('reject') || s.includes('fail') || s.includes('critical') || s.includes('bad') || s.includes('negative')) badgeClass = "bg-rose-100 text-rose-700";
    else if (s.includes('check') || s.includes('risk') || s.includes('conditional')) badgeClass = "bg-amber-100 text-amber-700";

    return (
        <div className="p-3 border rounded-lg bg-white shadow-sm flex flex-col justify-between h-full">
            <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-muted-foreground uppercase">{title}</span>
                {title === 'DSCR' && <Banknote className="w-3.5 h-3.5 text-slate-400" />}
                {title.includes('Ratio') && <Percent className="w-3.5 h-3.5 text-slate-400" />}
                {title.includes('Solvency') && <ArrowDownRight className="w-3.5 h-3.5 text-slate-400" />}
            </div>
            <div>
                <div className="text-lg font-bold text-slate-900">{value}</div>
                <div className="mt-1 flex items-center gap-1.5">
                    <Badge variant="outline" className={cn(
                        "text-[10px] h-5 px-1.5 font-medium border-0",
                        badgeClass
                    )}>
                        {status || 'N/A'}
                    </Badge>
                    {(s.includes('negative') || s.includes('fail')) && <div className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />}
                </div>
            </div>
        </div>
    );
};

const GateAnalysis = ({ gates, waterfallData }: { gates?: MemoCreditAnalysis['gates'], waterfallData?: WaterfallStep[] }) => {
    const [expandedGate, setExpandedGate] = useState<number | null>(null);

    // 1. Prepare Gate Data
    // If we have memo gates, use them. Else, reconstruct from waterfall data (heuristic grouping)
    let displayGates: any[] = [];

    if (gates && gates.length > 0) {
        displayGates = gates.map((g, i) => ({
            id: i,
            name: `${i + 1}. ${g.gate_name}`,
            status: g.status,
            passCount: g.checks.filter(c => c.status?.toLowerCase().includes('pass')).length,
            checks: g.checks
        }));
    } else if (waterfallData && waterfallData.length > 0) {
        // Mock grouping typical for this domain
        const groups = [
            { name: "1. Policy & Market", range: [0, 10] },
            { name: "2. Data Integrity", range: [10, 20] },
            { name: "3. Financial Assessment", range: [20, 30] },
            { name: "4. Final Verdict", range: [30, 99] }
        ];

        displayGates = groups.map((grp, i) => {
            const checks = waterfallData.filter(w => w.step_number >= grp.range[0] && w.step_number < grp.range[1]);
            if (checks.length === 0) return null;

            const passCount = checks.filter(c => c.result === 'Pass').length;
            const isAllPass = passCount === checks.length && checks.length > 0;

            return {
                id: i,
                name: grp.name,
                status: isAllPass ? 'Pass' : 'Fail',
                passCount: passCount,
                checks: checks.map(c => ({
                    name: c.rule_checked || c.scheme_name,
                    status: c.result === 'Pass' ? 'Pass' : 'Fail',
                    details: c.reason,
                    result: c.result
                }))
            };
        }).filter(Boolean);
    }

    if (displayGates.length === 0) return <div className="p-8 text-center text-muted-foreground border border-dashed rounded-lg bg-slate-50">No detailed gate analysis data available.</div>;

    // Toggle logic
    const toggleGate = (id: number) => setExpandedGate(expandedGate === id ? null : id);

    return (
        <Card className="border shadow-sm bg-white">
            <CardHeader className="pb-4">
                <CardTitle className="text-base font-bold text-slate-800">Gate Analysis</CardTitle>
                <CardDescription className="text-xs">Step-by-step logic flow determining the credit product fit</CardDescription>
            </CardHeader>
            <CardContent>
                {/* Horizontal Stepper */}
                <div className="relative flex items-center justify-between px-2 sm:px-6 py-6 overflow-x-auto">
                    {/* Connecting Line */}
                    <div className="absolute top-10 left-10 right-10 h-0.5 bg-slate-100 -z-0 hidden md:block" />

                    {displayGates.map((gate, idx) => {
                        const isPass = gate.status?.toLowerCase().includes('pass');
                        const isExpanded = expandedGate === gate.id;

                        return (
                            <div key={idx} className="relative z-10 flex flex-col items-center group cursor-pointer min-w-[80px]" onClick={() => toggleGate(gate.id)}>
                                <div className={cn(
                                    "w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all shadow-sm mb-3 bg-white",
                                    isPass ? "border-emerald-500 text-emerald-600" : "border-rose-400 text-rose-500",
                                    isExpanded ? "ring-2 ring-offset-1 ring-blue-100 scale-110" : "group-hover:scale-105"
                                )}>
                                    {isPass ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                                </div>
                                <span className="text-xs font-semibold text-slate-700 mb-1 max-w-[100px] text-center">{gate.name}</span>
                                <Badge variant="secondary" className={cn("text-[10px] px-1.5 h-5", isPass ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700")}>
                                    {gate.passCount} Pass
                                </Badge>
                            </div>
                        );
                    })}
                </div>

                {/* Detailed Checks Panel */}
                <div className="bg-slate-50 border rounded-lg p-0 overflow-hidden transition-all mt-4">
                    <div className="px-4 py-3 border-b flex items-center justify-between bg-white cursor-pointer" onClick={() => expandedGate !== null ? setExpandedGate(null) : null}>
                        <span className="text-sm font-semibold text-slate-800">
                            {expandedGate !== null ? `Checks: ${displayGates[expandedGate].name}` : 'Select a gate above to view details'}
                        </span>
                        {expandedGate !== null ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                    </div>

                    {expandedGate !== null ? (
                        <div className="divide-y max-h-[400px] overflow-y-auto">
                            {displayGates[expandedGate].checks.map((check: any, cIdx: number) => {
                                const checkPass = check.status?.toLowerCase().includes('pass') || check.result === 'Pass';
                                return (
                                    <div key={cIdx} className="px-4 py-3 flex items-start gap-3 hover:bg-slate-50/50">
                                        <div className="mt-0.5">
                                            {checkPass
                                                ? <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                                                : <XCircle className="w-4 h-4 text-rose-500" />
                                            }
                                        </div>
                                        <div className="flex-1 space-y-0.5">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm font-medium text-slate-700">{check.name}</span>
                                                <Badge variant="outline" className={cn(
                                                    "ml-2 text-[10px] h-5 border-0",
                                                    checkPass ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                                                )}>
                                                    {checkPass ? 'Pass' : 'Fail'}
                                                </Badge>
                                            </div>
                                            {!checkPass && check.details && (
                                                <p className="text-xs text-rose-600 mt-1 pl-0">
                                                    {check.details}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
                            <FileSearch className="w-8 h-8 opacity-20" />
                            <p>Click on any stage circle above to verify specific compliance rules.</p>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};


const DecisionOverview = ({ data, memoData, loanAmountRequested }: { data: CreditEngineData | null | undefined, memoData: MemoCreditAnalysis | null | undefined, loanAmountRequested?: string }) => {
    const rawStatus = data?.status || memoData?.recommendation || "Pending";
    const status = rawStatus.toUpperCase();

    // Theme Logic
    let statusConfig = {
        icon: AlertCircle,
        colorClass: "text-blue-700",
        bgClass: "bg-blue-50",
        title: "Under Review"
    };

    if (status.includes("APPROVE") || status.includes("ELIGIBLE") || status.includes("CLEARED")) {
        statusConfig = { icon: CheckCircle2, colorClass: "text-emerald-700", bgClass: "bg-emerald-50", title: "Approved" };
    } else if (status.includes("REJECT") || status.includes("FAILED")) {
        statusConfig = { icon: XCircle, colorClass: "text-rose-700", bgClass: "bg-rose-50", title: "Rejected" };
    } else if (status.includes("CONDITIONAL")) {
        statusConfig = { icon: AlertTriangle, colorClass: "text-amber-700", bgClass: "bg-amber-50", title: "Conditional" };
    }

    const StatusIcon = statusConfig.icon;
    // Prefer Memo Verdict if available as it is more descriptive
    const verdictText = memoData?.final_verdict || "Assessment complete based on provided financial data.";

    // Conditions / Rejections
    const issues = (status.includes("REJECT"))
        ? (data?.rejection_reasons || memoData?.rejection_reasons || [])
        : (data?.compliance_notes?.length ? data.compliance_notes : (memoData?.conditions || []));

    // Fallback conditions for visual completeness if empty (demo purposes based on screenshot instruction)
    const displayIssues = issues.length > 0 ? issues : (status.includes("REJECT") ? ["Specific rejection criteria not listed details available in Note."] : []);

    const requested = loanAmountRequested ? `₹${loanAmountRequested}` : (memoData?.loan_amount_requested || "N/A");
    const mpbf = data?.max_permissible_limit ? formatCurrency(data.max_permissible_limit) : (memoData?.max_permissible_limit || "N/A");
    // Fix: Handle 0 explicitly
    const sanctionedValue = data?.recommended_amount !== undefined ? data.recommended_amount : memoData?.sanction_amount;
    const sanctioned = sanctionedValue !== undefined ? formatCurrency(Number(sanctionedValue)) : "N/A";

    const cgtmse = (data?.cgtmse_eligible || memoData?.cgtmse_eligible) ? "Eligible" : "Not Eligible";
    const evaluatedScheme = data?.eligible_scheme || "Standard Assessment";

    return (
        <Card className="border-0 shadow-sm ring-1 ring-slate-200 bg-white mb-6">
            <CardHeader className="pb-2 border-b border-slate-100">
                <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Credit Decision Overview</CardTitle>
            </CardHeader>
            <CardContent className="pt-6">

                {/* 1. Big Status Header */}
                <div className="flex flex-col gap-1 mb-6">
                    <div className="flex items-center gap-3">
                        <StatusIcon className={cn("w-8 h-8", statusConfig.colorClass)} />
                        <h2 className={cn("text-3xl font-bold tracking-tight", "text-slate-900")}>
                            {statusConfig.title}
                        </h2>
                        {/* Scheme Badge next to Status */}
                        <Badge variant="outline" className="ml-2 text-sm font-medium border-slate-300 text-slate-600 bg-slate-50">
                            Scheme: {evaluatedScheme}
                        </Badge>
                    </div>
                    {/* Reason Text immediately below status usually */}
                    {displayIssues.length > 0 && (
                        <div className="mt-1 text-sm font-medium text-slate-600 flex flex-wrap gap-x-1 items-center">
                            <span className={status.includes("REJECT") ? "text-rose-600 font-bold" : "text-amber-600 font-bold"}>
                                {status.includes("REJECT") ? "Rejection Reason:" : "Condition:"}
                            </span>
                            <span>{displayIssues[0]}</span>
                        </div>
                    )}
                </div>

                {/* 2. Key Figures Row */}
                <div className="flex flex-col md:flex-row gap-4 mb-6">
                    <div className="flex-1 p-3 rounded-md border bg-white shadow-sm">
                        <p className="text-xs text-muted-foreground font-semibold mb-1">Requested</p>
                        <p className="text-xl font-bold text-slate-900">{requested}</p>
                    </div>
                    <div className="flex-1 p-3 rounded-md border bg-white shadow-sm">
                        <p className="text-xs text-muted-foreground font-semibold mb-1">MPBF Limit</p>
                        <p className="text-xl font-bold text-slate-900">{mpbf}</p>
                    </div>
                    <div className="flex-1 p-3 rounded-md border bg-white shadow-sm">
                        <p className="text-xs text-muted-foreground font-semibold mb-1">Eligible Sanction Amt</p>
                        <p className="text-xl font-bold text-slate-900">{sanctioned}</p>
                    </div>
                    <div className={cn("flex-1 p-3 rounded-md border shadow-sm flex flex-col justify-center", cgtmse === 'Eligible' ? "bg-blue-50/50 border-blue-100" : "bg-slate-50")}>
                        <p className="text-xs text-muted-foreground font-semibold mb-0.5">CGTMSE Cover</p>
                        <div className="flex items-center gap-1.5">
                            {cgtmse === 'Eligible' ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Info className="w-4 h-4 text-slate-400" />}
                            <span className={cn("text-lg font-bold", cgtmse === 'Eligible' ? "text-emerald-700" : "text-slate-600")}>{cgtmse}</span>
                        </div>
                    </div>
                </div>

                {/* 3. Verdict Text */}
                <div className="bg-slate-50 rounded-md p-3 text-sm text-slate-700 leading-relaxed border border-slate-100">
                    <span className="font-semibold text-slate-900 mr-1">Analyst Verdict:</span>
                    {verdictText}
                </div>

            </CardContent>
        </Card>
    );
};

const WorkingCapitalCard = ({ data }: { data: CreditEngineData['working_capital_analysis'] }) => {
    if (!data || (!data.gross_wc && !data.mpbf)) return null;

    const isNayak = data.method_code === 'NAYAK' || data.method?.toLowerCase().includes('turnover');
    const methodLabel = data.method_used || data.method || (isNayak ? 'Turnover Method (Nayak)' : 'MPBF Method II (Tandon)');
    const eligibleFinance = data.eligible_bank_finance || data.mpbf || 0;

    // For Nayak Method (Turnover)
    if (isNayak) {
        const projectedTurnover = data.projected_turnover || data.gross_wc / 0.25;
        const grossWC = data.gross_working_capital_need || data.gross_wc || projectedTurnover * 0.25;
        const promoterMargin = data.promoter_contribution_5_percent || data.margin || projectedTurnover * 0.05;

        const p_gross = 100;
        const p_margin = (promoterMargin / grossWC) * 100;

        return (
            <Card className="border shadow-sm bg-white">
                <CardHeader className="pb-4">
                    <CardTitle className="text-base font-bold text-slate-800 flex justify-between">
                        <span>Working Capital Logic</span>
                        <Badge variant="outline" className="text-xs font-normal text-slate-500">{methodLabel}</Badge>
                    </CardTitle>
                    <CardDescription className="text-xs">Breakdown of how the credit limit was sized (Nayak Committee)</CardDescription>
                </CardHeader>
                <CardContent>
                    {/* Visual Stacked Bar for Turnover Method */}
                    <div className="h-8 w-full flex rounded-md overflow-hidden mb-4 ring-1 ring-slate-200">
                        <div style={{ width: '20%' }} className="bg-amber-200" title={`Promoter Margin (5%)`} />
                        <div style={{ width: '80%' }} className="bg-blue-500" title={`Bank Finance (20%)`} />
                    </div>

                    {/* Legend / Key Figures */}
                    <div className="space-y-3 text-sm">
                        <div className="flex justify-between items-center border-b pb-2">
                            <span className="text-muted-foreground">Projected Annual Turnover</span>
                            <span className="font-semibold">{formatCurrency(projectedTurnover)}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-sm bg-emerald-200" />
                                <span className="text-muted-foreground text-xs">Gross WC Requirement (25%)</span>
                            </div>
                            <span className="font-mono text-slate-600">{formatCurrency(grossWC)}</span>
                        </div>
                        <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-sm bg-amber-200" />
                                <span className="text-muted-foreground text-xs">Less: Promoter Margin (5%)</span>
                            </div>
                            <span className="font-mono text-amber-700">-{formatCurrency(promoterMargin)}</span>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t mt-2 bg-blue-50/50 p-2 rounded">
                            <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-sm bg-blue-500" />
                                <span className="font-bold text-blue-900">Eligible Bank Finance (20%)</span>
                            </div>
                            <span className="font-bold text-blue-700 text-lg">{formatCurrency(eligibleFinance)}</span>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    // For Tandon Method II (Asset-Based MPBF)
    const totalCA = data.total_current_assets || data.gross_wc || 0;
    const ocl = data.other_current_liabilities || 0;
    const wcGap = data.working_capital_gap || data.wc_gap || (totalCA - ocl);
    const marginOnAssets = data.margin_on_assets_25_percent || data.margin || (totalCA * 0.25);

    // Percentages for stacked bar
    const p_ocl = totalCA > 0 ? (ocl / totalCA) * 100 : 0;
    const p_margin = totalCA > 0 ? (marginOnAssets / totalCA) * 100 : 0;
    const p_mpbf = totalCA > 0 ? (eligibleFinance / totalCA) * 100 : 0;

    return (
        <Card className="border shadow-sm bg-white">
            <CardHeader className="pb-4">
                <CardTitle className="text-base font-bold text-slate-800 flex justify-between">
                    <span>Working Capital Logic</span>
                    <Badge variant="outline" className="text-xs font-normal text-slate-500">{methodLabel}</Badge>
                </CardTitle>
                <CardDescription className="text-xs">Breakdown of how the credit limit (MPBF) was sized (Tandon Committee)</CardDescription>
            </CardHeader>
            <CardContent>
                {/* Visual Stacked Bar */}
                <div className="h-8 w-full flex rounded-md overflow-hidden mb-4 ring-1 ring-slate-200">
                    <div style={{ width: `${p_ocl}%` }} className="bg-slate-200" title={`Other Liabilities: ${formatCurrency(ocl)}`} />
                    <div style={{ width: `${p_margin}%` }} className="bg-amber-200" title={`Margin (25% of TCA): ${formatCurrency(marginOnAssets)}`} />
                    <div style={{ width: `${p_mpbf}%` }} className="bg-blue-500" title={`Bank Finance (MPBF): ${formatCurrency(eligibleFinance)}`} />
                </div>

                {/* Legend / Key Figures */}
                <div className="space-y-3 text-sm">
                    <div className="flex justify-between items-center border-b pb-2">
                        <span className="text-muted-foreground">Total Current Assets</span>
                        <span className="font-semibold">{formatCurrency(totalCA)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-sm bg-slate-200" />
                            <span className="text-muted-foreground text-xs">Less: Other Current Liabilities</span>
                        </div>
                        <span className="font-mono text-slate-600">-{formatCurrency(ocl)}</span>
                    </div>
                    <div className="flex justify-between items-center text-xs text-slate-500 pl-5">
                        <span>= Working Capital Gap</span>
                        <span className="font-mono">{formatCurrency(wcGap)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-sm bg-amber-200" />
                            <span className="text-muted-foreground text-xs">Less: Margin (25% of TCA)</span>
                        </div>
                        <span className="font-mono text-amber-700">-{formatCurrency(marginOnAssets)}</span>
                    </div>
                    <div className="flex justify-between items-center pt-2 border-t mt-2 bg-blue-50/50 p-2 rounded">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-sm bg-blue-500" />
                            <span className="font-bold text-blue-900">Maximum Permissible Bank Finance</span>
                        </div>
                        <span className="font-bold text-blue-700 text-lg">{formatCurrency(eligibleFinance)}</span>
                    </div>
                    {data.surplus_liquidity && (
                        <div className="flex items-center gap-2 p-2 bg-emerald-50 rounded text-emerald-700 text-xs">
                            <CheckCircle2 className="w-4 h-4" />
                            <span>Surplus Liquidity - No bank finance needed</span>
                        </div>
                    )}
                    {data.conservative_adjustment && (
                        <div className="flex items-center gap-2 p-2 bg-amber-50 rounded text-amber-700 text-xs">
                            <AlertTriangle className="w-4 h-4" />
                            <span>{data.conservative_adjustment}</span>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};

// --- Scheme Eligibility Matrix Component ---
const SchemeEligibilityCard = ({ waterfallData }: { waterfallData: WaterfallStep[] | undefined }) => {
    if (!waterfallData || waterfallData.length === 0) return null;

    // Define schemes to track
    const schemes = [
        { key: "Mudra Yojana", label: "Pradhan Mantri Mudra Yojana" },
        { key: "CGTMSE", label: "CGTMSE (Collateral Free)" },
        { key: "CGSS", label: "CGSS (Startup India)" }, // Partial match check
        { key: "New Entity Loan", label: "New Entity Loan" },
        { key: "Business Installment Loan", label: "Business Installment Loan (BIL)" }
    ];

    return (
        <Card className="border shadow-sm bg-white mt-6">
            <CardHeader className="pb-3 border-b bg-slate-50/50">
                <CardTitle className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <FileSearch className="w-4 h-4 text-blue-600" />
                    Scheme Eligibility Matrix
                </CardTitle>
                <CardDescription className="text-xs">eligibility status across all available credit products</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
                <div className="divide-y">
                    {schemes.map((scheme) => {
                        // Find relevant step in waterfall
                        // We look for steps where scheme_name contains our key
                        const step = waterfallData.find(s => s.scheme_name.includes(scheme.key));

                        // Status Logic
                        // If no step found, it might have been skipped or not reached. Assume 'Not Check' or 'Fail'
                        const isEligible = step?.result?.toLowerCase() === 'pass';
                        const statusColor = isEligible ? "bg-emerald-100 text-emerald-700 border-emerald-200" : "bg-slate-100 text-slate-500 border-slate-200";
                        const icon = isEligible ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <XCircle className="w-4 h-4 text-slate-400" />;

                        return (
                            <div key={scheme.key} className="flex items-center justify-between p-3 hover:bg-slate-50 transition-colors">
                                <div className="flex flex-col gap-0.5">
                                    <span className="text-sm font-medium text-slate-800">{scheme.label}</span>
                                    {step?.reason && !isEligible && (
                                        <span className="text-xs text-rose-600 font-medium">Reason: {step.reason}</span>
                                    )}
                                    {isEligible && (
                                        <span className="text-xs text-emerald-600 font-medium">{step?.reason || "Condition met"}</span>
                                    )}
                                </div>
                                <Badge variant="outline" className={cn("flex items-center gap-1.5 h-6 ml-4 shrink-0", statusColor)}>
                                    {icon}
                                    {isEligible ? "Eligible" : "Not Eligible"}
                                </Badge>
                            </div>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
};

// --- Main Component ---

export default function CreditEngine({ data, memoCreditData, dealId, loanAmountRequested }: CreditEngineProps) {
    const [overrideOpen, setOverrideOpen] = useState(false);
    const [overrideRule, setOverrideRule] = useState('');
    const [overrideJustification, setOverrideJustification] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const { toast } = useToast();

    // --- Data Preparation Helpers ---
    // Safe parsing helper
    const safeParse = (val: any) => {
        if (typeof val === 'number') return val;
        if (!val) return 0;
        return parseFloat(String(val).replace(/[^0-9.-]/g, '')) || 0;
    };

    const effectiveCurrentRatio = (data?.current_ratio && data.current_ratio > 0)
        ? data.current_ratio
        : safeParse(memoCreditData?.current_ratio);

    const effectiveDSCR = (data?.avg_dscr && data.avg_dscr > 0)
        ? data.avg_dscr
        : safeParse(memoCreditData?.dscr);

    const effectiveTolTnw = (data?.tol_tnw && data.tol_tnw > 0)
        ? data.tol_tnw
        : safeParse(memoCreditData?.tol_tnw_ratio);

    const crStatus = data?.current_ratio_status === "No Data" ? (effectiveCurrentRatio >= 1.33 ? 'Eligible' : 'Check') : (data?.current_ratio_status || 'N/A');
    const dscrStatus = data?.dscr_status === "No Data" ? (effectiveDSCR >= 1.25 ? 'Safe' : effectiveDSCR < 0 ? 'Negative' : 'Low') : (data?.dscr_status || 'N/A');
    const levStatus = data?.leverage_status === "No Data" ? (effectiveTolTnw <= 3 ? 'Safe' : 'High Risk') : (data?.leverage_status || 'N/A');

    // Helper function to convert memo summary to radar chart data
    const deriveRadarFromMemo = (memo: MemoCreditAnalysis): Record<string, number> => {
        const radarData: Record<string, number> = {};
        const parseValue = (val: string | number | undefined): number => {
            if (val === undefined || val === null) return 0;
            if (typeof val === 'number') return val;
            const num = parseFloat(String(val).replace(/[^0-9.-]/g, ''));
            return isNaN(num) ? 0 : num;
        };
        // Normalize 
        if (memo.current_ratio) radarData['Current Ratio'] = Math.min(parseValue(memo.current_ratio) * 50, 100);
        if (memo.dscr) radarData['DSCR'] = Math.min(parseValue(memo.dscr) * 50, 100);
        if (memo.tol_tnw_ratio) radarData['Leverage'] = Math.max(100 - parseValue(memo.tol_tnw_ratio) * 20, 0);

        // Add gate-based scores
        memo.gates?.forEach(gate => {
            const passCount = gate.checks?.filter(c => c.status?.toLowerCase().includes('pass')).length || 0;
            const totalChecks = gate.checks?.length || 1;
            radarData[gate.gate_name] = (passCount / totalChecks) * 100;
        });
        return radarData;
    };

    // Normalize radar data for proper display (0-100 scale)
    const normalizeRadarData = (radar: Record<string, number>): Record<string, number> => {
        const normalized: Record<string, number> = {};

        // Normalize each metric to 0-100 scale based on banking benchmarks
        for (const [key, value] of Object.entries(radar)) {
            const keyLower = key.toLowerCase();
            if (keyLower.includes('dscr')) {
                // DSCR: 1.0 = 50, 2.0+ = 100, < 1 = proportional
                normalized[key] = Math.min(Math.max((value / 2) * 100, 0), 100);
            } else if (keyLower.includes('current') || keyLower.includes('cr')) {
                // Current Ratio: 1.33 = 75, 2.0+ = 100
                normalized[key] = Math.min(Math.max((value / 2) * 100, 0), 100);
            } else if (keyLower.includes('tol') || keyLower.includes('leverage')) {
                // TOL/TNW: Lower is better. 3.0 = 50, 0 = 100, 6+ = 0
                normalized[key] = Math.max(100 - (value * 16.67), 0);
            } else {
                // Assume already 0-100 or use as-is capped
                normalized[key] = Math.min(Math.max(value, 0), 100);
            }
        }
        return normalized;
    };

    const effectiveRadar = (data?.radar_chart_data && Object.keys(data.radar_chart_data).length > 0)
        ? normalizeRadarData(data.radar_chart_data)
        : (memoCreditData ? deriveRadarFromMemo(memoCreditData) : {
            'DSCR': Math.min(Math.max((effectiveDSCR / 2) * 100, 0), 100),
            'Current Ratio': Math.min(Math.max((effectiveCurrentRatio / 2) * 100, 0), 100),
            'Leverage': Math.max(100 - (effectiveTolTnw * 16.67), 0),
            'Profitability': 50, // Default
            'Liquidity': 50  // Default
        });

    const chartData = Object.entries(effectiveRadar).map(([key, value]) => ({
        subject: key,
        score: value,
        fullMark: 100,
    }));

    // Calculate dynamic credit score (weighted average of normalized scores)
    const creditScore = chartData.length > 0
        ? Math.round(chartData.reduce((sum, item) => sum + item.score, 0) / chartData.length)
        : 0;

    // Data missing handling
    if (!data && !memoCreditData) {
        return (
            <Card className="border-dashed h-[400px] flex flex-col items-center justify-center">
                <Landmark className="w-12 h-12 text-muted-foreground mb-4 opacity-20" />
                <h3 className="text-lg font-semibold text-slate-700">Credit Engine Assessment</h3>
                <p className="text-muted-foreground text-sm">Waiting for financial data to be processed...</p>
                <Button variant="outline" className="mt-4">Refresh Analysis</Button>
            </Card>
        );
    }

    return (
        <div className="space-y-6 max-w-[1400px] mx-auto pb-12">

            {/* 1. Full Width Decision Card */}
            <DecisionOverview data={data} memoData={memoCreditData} loanAmountRequested={loanAmountRequested} />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

                {/* 2. LEFT/MAIN COLUMN: Gate Analysis (8 cols) */}
                <div className="lg:col-span-8 flex flex-col gap-6">
                    {/* Scheme Eligibility Matrix */}
                    <SchemeEligibilityCard waterfallData={data?.waterfall_data} />

                    <GateAnalysis gates={memoCreditData?.gates} waterfallData={data?.waterfall_data} />

                    {/* Working Capital Breakdown */}
                    {data?.working_capital_analysis && (
                        <WorkingCapitalCard data={data.working_capital_analysis} />
                    )}
                </div>

                {/* 3. RIGHT COLUMN: Financial DNA & Metrics (4 cols) */}
                <div className="lg:col-span-4 flex flex-col gap-6">

                    {/* Financial DNA Card */}
                    <Card className="border shadow-sm bg-white">
                        <CardHeader className="pb-2 border-b bg-slate-50/50">
                            <CardTitle className="text-sm font-bold text-slate-800 flex items-center gap-2">
                                <Activity className="w-4 h-4 text-blue-600" />
                                Financial DNA
                            </CardTitle>
                            <CardDescription className="text-xs">Scoring against bank benchmarks</CardDescription>
                        </CardHeader>
                        <CardContent className="p-2 relative min-h-[300px]">
                            <ResponsiveContainer width="100%" height={250}>
                                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
                                    <PolarGrid stroke="#e2e8f0" />
                                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748b', fontSize: 10 }} />
                                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                                    <Radar
                                        name="Credit Score"
                                        dataKey="score"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        fill="#3b82f6"
                                        fillOpacity={0.15}
                                    />
                                    <Tooltip contentStyle={{ borderRadius: '8px', fontSize: '12px' }} />
                                </RadarChart>
                            </ResponsiveContainer>

                            {/* Score Strip */}
                            <div className="mt-2 mx-2 p-2 bg-slate-100 rounded flex justify-between items-center text-xs">
                                <span className="font-semibold text-slate-600">Credit Score: {creditScore} / 100</span>
                                <span className={cn(
                                    "font-medium flex items-center gap-1",
                                    creditScore >= 70 ? "text-emerald-600" : creditScore >= 40 ? "text-amber-600" : "text-rose-600"
                                )}>
                                    {creditScore >= 70 ? 'Good' : creditScore >= 40 ? 'Average' : 'Poor'}
                                    <ArrowRight className="w-3 h-3" />
                                    {creditScore >= 70 ? 'Eligible' : creditScore >= 40 ? 'Review' : 'Risk'}
                                </span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Key Ratios Row (Stacked) */}
                    <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-2 gap-3">
                        <div className="col-span-1">
                            <MetricTile
                                title="Quick Ratio"
                                value={effectiveCurrentRatio.toFixed(2)}
                                status={crStatus}
                                footer={false}
                            />
                        </div>
                        <div className="col-span-1">
                            <MetricTile
                                title="Solvency"
                                value={effectiveTolTnw.toFixed(2) + 'x'}
                                status={levStatus}
                                footer={false}
                            />
                        </div>
                        <div className="col-span-2">
                            <MetricTile
                                title="DSCR"
                                value={effectiveDSCR.toFixed(2)}
                                status={dscrStatus}
                                footer={true}
                            />
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="space-y-3">
                        <Dialog open={overrideOpen} onOpenChange={setOverrideOpen}>
                            <DialogTrigger asChild>
                                <Button className="w-full bg-blue-900 hover:bg-blue-800 text-white shadow-md">
                                    Request Override
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-[500px]">
                                <DialogHeader>
                                    <DialogTitle className="flex items-center gap-2">
                                        <AlertTriangle className="w-5 h-5 text-amber-500" />
                                        Request Managerial Override
                                    </DialogTitle>
                                    <DialogDescription>
                                        Override a specific risk gate. This action will be logged for compliance audit.
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="grid gap-4 py-4">
                                    <div className="grid gap-2">
                                        <Label htmlFor="rule">Rule to Override</Label>
                                        <Select value={overrideRule} onValueChange={setOverrideRule}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select a rule..." />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="leverage_check">Leverage Check (TOL/TNW)</SelectItem>
                                                <SelectItem value="dscr_check">DSCR Check</SelectItem>
                                                <SelectItem value="liquidity_check">Liquidity Check (CR)</SelectItem>
                                                <SelectItem value="vintage_check">Vintage Requirement</SelectItem>
                                                <SelectItem value="profitability_check">Profitability Requirement</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="justification">Business Justification</Label>
                                        <Textarea
                                            id="justification"
                                            placeholder="Minimum 20 characters. E.g., Strong order book from Fortune 500 client..."
                                            value={overrideJustification}
                                            onChange={(e) => setOverrideJustification(e.target.value)}
                                            className="min-h-[100px]"
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            {overrideJustification.length}/20 characters minimum
                                        </p>
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button variant="outline" onClick={() => setOverrideOpen(false)}>Cancel</Button>
                                    <Button
                                        disabled={isSubmitting || !overrideRule || overrideJustification.length < 20 || !dealId}
                                        onClick={async () => {
                                            if (!dealId) return;
                                            setIsSubmitting(true);
                                            try {
                                                const response = await authenticatedFetch(
                                                    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/credit/override`,
                                                    {
                                                        method: 'POST',
                                                        headers: { 'Content-Type': 'application/json' },
                                                        body: JSON.stringify({
                                                            deal_id: dealId,
                                                            rule_id: overrideRule,
                                                            justification: overrideJustification,
                                                            analyst_id: 'current_user' // Will be replaced by backend
                                                        })
                                                    }
                                                );
                                                if (!response.ok) throw new Error('Override request failed');
                                                toast({
                                                    title: "Override Applied",
                                                    description: "Status updated to Conditional Approval. Refresh to see changes.",
                                                });
                                                setOverrideOpen(false);
                                                setOverrideRule('');
                                                setOverrideJustification('');
                                            } catch (error: any) {
                                                toast({
                                                    variant: "destructive",
                                                    title: "Override Failed",
                                                    description: error.message,
                                                });
                                            } finally {
                                                setIsSubmitting(false);
                                            }
                                        }}
                                    >
                                        {isSubmitting ? 'Submitting...' : 'Submit Override'}
                                    </Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                        <Button variant="outline" className="w-full">
                            View CMA Report
                        </Button>
                    </div>

                </div>
            </div>
        </div>
    );
}
