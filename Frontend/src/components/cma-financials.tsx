'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Building2, FileSpreadsheet, Scale, Banknote, Info } from 'lucide-react';

// Types for CMA Data
interface CMARow {
    particulars: string;
    values: string[];
}

interface CMATable {
    years: string[];
    rows: CMARow[];
}

interface CMAData {
    general_info: Record<string, any>;
    operating_statement: CMATable;
    balance_sheet: CMATable;
    cash_flow: CMATable;
}

interface CMAFinancialsProps {
    data: CMAData | null | undefined;
}

// Component to render a key-value grid for General Info
const GeneralInfoSection = ({ data }: { data: Record<string, any> }) => {
    const entries = Object.entries(data);

    if (entries.length === 0) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                No general information available
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {entries.map(([key, value]) => (
                <div key={key} className="flex flex-col p-3 bg-secondary/30 rounded-lg">
                    <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{key}</span>
                    <span className="text-sm font-semibold mt-1">
                        {typeof value === 'object' && value !== null
                            ? (Array.isArray(value) ? value.join(', ') : JSON.stringify(value, null, 2))
                            : (value || 'N/A')}
                    </span>
                </div>
            ))}
        </div>
    );
};

// Component to render a financial table (Operating Statement, Balance Sheet, Cash Flow)
const FinancialTable = ({ data }: { data: CMATable }) => {
    if (!data.years || data.years.length === 0 || !data.rows || data.rows.length === 0) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                No data available for this section
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <Table>
                <TableHeader>
                    <TableRow className="bg-secondary/50">
                        <TableHead className="font-bold min-w-[250px]">Particulars</TableHead>
                        {data.years.map((year, idx) => (
                            <TableHead key={idx} className="text-right font-bold min-w-[120px]">
                                {year}
                            </TableHead>
                        ))}
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {data.rows.map((row, rowIdx) => {
                        // Check if this is a header/section row (usually all values are 0.00 or empty)
                        const isHeaderRow = row.values.every(v => v === '0.00' || v === '0' || v === '');
                        const isTotalRow = row.particulars.toLowerCase().includes('total') ||
                            row.particulars.toLowerCase().includes('net worth') ||
                            row.particulars.toLowerCase().includes('gross profit');

                        return (
                            <TableRow
                                key={rowIdx}
                                className={`
                  ${isHeaderRow ? 'bg-primary/5 font-semibold' : ''}
                  ${isTotalRow ? 'bg-accent/10 font-bold border-t-2' : ''}
                  hover:bg-secondary/30 transition-colors
                `}
                            >
                                <TableCell className={`${isHeaderRow || isTotalRow ? 'font-semibold' : ''}`}>
                                    {row.particulars}
                                </TableCell>
                                {row.values.map((value, valIdx) => {
                                    const numValue = parseFloat(value);
                                    const isNegative = !isNaN(numValue) && numValue < 0;

                                    return (
                                        <TableCell
                                            key={valIdx}
                                            className={`text-right ${isNegative ? 'text-red-500' : ''} ${isTotalRow ? 'font-bold' : ''}`}
                                        >
                                            {value}
                                        </TableCell>
                                    );
                                })}
                            </TableRow>
                        );
                    })}
                </TableBody>
            </Table>
        </div>
    );
};

export default function CMAFinancials({ data }: CMAFinancialsProps) {
    if (!data) {
        return (
            <Card>
                <CardContent className="py-8">
                    <div className="text-center text-muted-foreground">
                        <FileSpreadsheet className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No CMA data available</p>
                        <p className="text-sm mt-2">Upload a CMA report to view financial details</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            <Tabs defaultValue="general" className="w-full">
                <TabsList className="grid w-full grid-cols-4 mb-4">
                    <TabsTrigger value="general" className="flex items-center gap-2">
                        <Building2 className="w-4 h-4" />
                        <span className="hidden sm:inline">General Info</span>
                    </TabsTrigger>
                    <TabsTrigger value="operating" className="flex items-center gap-2">
                        <FileSpreadsheet className="w-4 h-4" />
                        <span className="hidden sm:inline">Operating</span>
                    </TabsTrigger>
                    <TabsTrigger value="balance" className="flex items-center gap-2">
                        <Scale className="w-4 h-4" />
                        <span className="hidden sm:inline">Balance Sheet</span>
                    </TabsTrigger>
                    <TabsTrigger value="cashflow" className="flex items-center gap-2">
                        <Banknote className="w-4 h-4" />
                        <span className="hidden sm:inline">Cash Flow</span>
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="general">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Building2 className="w-5 h-5 text-primary" />
                                General Information
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <GeneralInfoSection data={data.general_info || {}} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="operating">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileSpreadsheet className="w-5 h-5 text-primary" />
                                Operating Statement
                                {data.operating_statement?.years?.length > 0 && (
                                    <Badge variant="outline" className="ml-2">
                                        {data.operating_statement.years.length} Years
                                    </Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <FinancialTable data={data.operating_statement || { years: [], rows: [] }} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="balance">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Scale className="w-5 h-5 text-primary" />
                                Balance Sheet
                                {data.balance_sheet?.years?.length > 0 && (
                                    <Badge variant="outline" className="ml-2">
                                        {data.balance_sheet.years.length} Years
                                    </Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <FinancialTable data={data.balance_sheet || { years: [], rows: [] }} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="cashflow">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Banknote className="w-5 h-5 text-primary" />
                                Cash Flow Statement
                                {data.cash_flow?.years?.length > 0 && (
                                    <Badge variant="outline" className="ml-2">
                                        {data.cash_flow.years.length} Years
                                    </Badge>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <FinancialTable data={data.cash_flow || { years: [], rows: [] }} />
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
