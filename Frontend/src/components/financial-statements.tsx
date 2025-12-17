import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, TrendingUp, Landmark, Percent } from 'lucide-react';

interface FinancialYear {
    year: string;
    tier?: string;
    [key: string]: any;
}

interface FinancialStatementsProps {
    data: {
        audited_financials: FinancialYear[];
        provisional_financials: FinancialYear | null;
        projected_financials: FinancialYear[];
    } | undefined;
}

const formatCurrency = (val: number | string) => {
    if (!val && val !== 0) return '-';
    const num = parseFloat(String(val));
    if (isNaN(num)) return '-';
    // Format to INR Cr or Lakhs automatically? Or just standard INR with commas
    // User requested "absolute figures to full numbers" in extraction, but for display, full numbers might be long.
    // Let's us readable format (commas).
    return new Intl.NumberFormat('en-IN', {
        maximumFractionDigits: 0
    }).format(num);
};

const formatRatio = (val: number | string) => {
    if (!val && val !== 0) return '-';
    const num = parseFloat(String(val));
    if (isNaN(num)) return '-';
    return num.toFixed(2);
};

export default function FinancialStatements({ data }: FinancialStatementsProps) {
    // Debug: Log the incoming data
    console.log('📊 FinancialStatements received data:', data);

    if (!data) {
        return (
            <Card className="border-dashed py-12 text-center">
                <div className="flex flex-col items-center justify-center text-muted-foreground">
                    <FileText className="w-12 h-12 mb-4 opacity-20" />
                    <p>No processed financial statements available.</p>
                </div>
            </Card>
        );
    }

    // Combine all years into a single timeline sorted by year
    const allYears: FinancialYear[] = [
        ...(data.audited_financials || []),
        ...(data.provisional_financials ? [data.provisional_financials] : []),
        ...(data.projected_financials || [])
    ].sort((a, b) => {
        // Simple string sort for FY might work if format is consistent (FY23, FY24)
        return a.year.localeCompare(b.year);
    });

    if (allYears.length === 0) {
        return (
            <Card className="border-dashed py-12 text-center">
                <div className="flex flex-col items-center justify-center text-muted-foreground">
                    <FileText className="w-12 h-12 mb-4 opacity-20" />
                    <p>No financial statements data found.</p>
                </div>
            </Card>
        );
    }

    // Define Sections
    const sections = [
        {
            title: "Operating Performance (P&L)",
            icon: <TrendingUp className="w-4 h-4 mr-2" />,
            rows: [
                { label: "Gross Turnover / Revenue", key: "revenue", format: formatCurrency, bold: true },
                { label: "EBITDA", key: "ebitda", format: formatCurrency },
                { label: "Interest Expense", key: "interest_expense", format: formatCurrency },
                { label: "Depreciation", key: "depreciation", format: formatCurrency },
                { label: "Profit After Tax (PAT)", key: "pat", format: formatCurrency, bold: true },
                { label: "Cash Profit", key: "cash_profit", format: formatCurrency },
            ]
        },
        {
            title: "Financial Position (Balance Sheet)",
            icon: <Landmark className="w-4 h-4 mr-2" />,
            rows: [
                { label: "Tangible Net Worth", key: "tangible_net_worth", format: formatCurrency, bold: true },
                { label: "Total Debt", key: "total_debt", format: formatCurrency },
                { label: "Long Term Debt", key: "long_term_debt", format: formatCurrency, indent: true },
                { label: "Short Term Debt", key: "short_term_debt", format: formatCurrency, indent: true },
                { label: "Current Assets", key: "current_assets", format: formatCurrency },
                { label: "Current Liabilities", key: "current_liabilities", format: formatCurrency },
                { label: "Net Working Capital", key: "net_working_capital", format: formatCurrency },
                { label: "Fixed Assets", key: "fixed_assets", format: formatCurrency },
            ]
        },
        {
            title: "Key Credit Ratios",
            icon: <Percent className="w-4 h-4 mr-2" />,
            rows: [
                { label: "DSCR", key: "dscr", format: formatRatio, bold: true },
                { label: "ISCR", key: "iscr", format: formatRatio },
                { label: "Current Ratio", key: "current_ratio", format: formatRatio, bold: true },
                { label: "TOL/TNW", key: "tol_tnw", format: formatRatio },
                { label: "Debt/Equity", key: "debt_equity_ratio", format: formatRatio },
            ]
        }
    ];

    return (
        <div className="space-y-6">
            {sections.map((section, idx) => (
                <Card key={idx} className="shadow-sm">
                    <CardHeader className="py-4 bg-slate-50/50 border-b">
                        <CardTitle className="text-base font-semibold flex items-center text-slate-800">
                            {section.icon}
                            {section.title}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 overflow-x-auto">
                        <Table>
                            <TableHeader>
                                <TableRow className="hover:bg-transparent">
                                    <TableHead className="w-[250px] font-bold text-slate-700">Particulars</TableHead>
                                    {allYears.map((fy, i) => (
                                        <TableHead key={i} className="text-right min-w-[120px]">
                                            <div className="flex flex-col items-end gap-1 py-2">
                                                <span className="font-bold text-slate-900">{fy.year}</span>
                                                <Badge variant="outline" className={`text-[10px] h-5 px-1.5 font-normal border-0 ${fy.tier?.toLowerCase().includes('audited') ? 'bg-emerald-100 text-emerald-700' :
                                                    fy.tier?.toLowerCase().includes('provisional') ? 'bg-blue-100 text-blue-700' :
                                                        'bg-amber-100 text-amber-700'
                                                    }`}>
                                                    {fy.tier || 'Unknown'}
                                                </Badge>
                                            </div>
                                        </TableHead>
                                    ))}
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {section.rows.map((row, rIdx) => (
                                    <TableRow key={rIdx} className={rIdx % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}>
                                        <TableCell className={`
                                            ${row.bold ? 'font-bold text-slate-800' : 'font-medium text-slate-600'}
                                            ${row.indent ? 'pl-8 text-sm' : ''}
                                        `}>
                                            {row.label}
                                        </TableCell>
                                        {allYears.map((fy, cIdx) => (
                                            <TableCell key={cIdx} className="text-right font-mono text-slate-700">
                                                {row.format(fy[row.key])}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            ))}

            {/* Disclaimer */}
            <div className="flex items-center gap-2 p-4 bg-yellow-50 text-yellow-800 rounded-md border border-yellow-200 text-sm">
                <Landmark className="w-4 h-4" />
                <p><strong>Note:</strong> Data extracted from provided CMA documents. Ratios strictly derived from extracted figures.</p>
            </div>
        </div>
    );
}
