'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { FileSpreadsheet, Building2, Scale, Banknote } from 'lucide-react';

// Types for dynamic CMA Data (new format)
interface CMARow {
    particulars: string;
    values: string[];
}

interface CMASheet {
    name: string;
    first_column_header?: string;
    years: string[];
    rows: CMARow[];
}

// New dynamic format
interface CMADataNew {
    sheets: CMASheet[];
    sheet_count: number;
}

// Old fixed format
interface CMATable {
    years: string[];
    rows: CMARow[];
}

interface CMADataOld {
    general_info?: Record<string, any>;
    operating_statement?: CMATable;
    balance_sheet?: CMATable;
    cash_flow?: CMATable;
}

interface CMAFinancialsProps {
    data: CMADataNew | CMADataOld | null | undefined;
}

// Component to render key-value pairs (for General Info)
const GeneralInfoSection = ({ data }: { data: Record<string, any> }) => {
    const entries = Object.entries(data || {});

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

// Component to render a financial table (any sheet)
const SheetTable = ({ data }: { data: CMATable | CMASheet }) => {
    const years = data?.years || [];
    const rows = data?.rows || [];
    const firstColumnHeader = (data as CMASheet)?.first_column_header || 'Particulars';

    if (rows.length === 0) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                No data available for this sheet
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <Table>
                <TableHeader>
                    <TableRow className="bg-secondary/50">
                        <TableHead className="font-bold min-w-[250px]">{firstColumnHeader}</TableHead>
                        {years.map((year, idx) => (
                            <TableHead key={idx} className="text-right font-bold min-w-[120px]">
                                {year}
                            </TableHead>
                        ))}
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {rows.map((row, rowIdx) => {
                        // Defensive check: ensure row and values exist
                        if (!row || !Array.isArray(row.values)) return null;

                        // Check if this is a header/section row
                        const isHeaderRow = row.values.every(v => v === '0.00' || v === '0' || v === '' || v === '0.0');
                        const isTotalRow = row.particulars?.toLowerCase()?.includes('total') ||
                            row.particulars?.toLowerCase()?.includes('net worth') ||
                            row.particulars?.toLowerCase()?.includes('gross profit');

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

// Check if data is new format (has sheets array)
function isNewFormat(data: any): data is CMADataNew {
    return data && Array.isArray(data.sheets);
}

export default function CMAFinancials({ data }: CMAFinancialsProps) {
    // Debug logging
    console.log('CMAFinancials received data:', data);

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

    // NEW FORMAT: Dynamic sheets
    if (isNewFormat(data)) {
        const sheets = data.sheets;

        if (sheets.length === 0) {
            return (
                <Card>
                    <CardContent className="py-8">
                        <div className="text-center text-muted-foreground">
                            <FileSpreadsheet className="w-12 h-12 mx-auto mb-4 opacity-50" />
                            <p>No sheets found in CMA data</p>
                        </div>
                    </CardContent>
                </Card>
            );
        }

        const defaultTab = sheets[0]?.name || 'sheet-0';

        return (
            <div className="space-y-4">
                <Tabs defaultValue={defaultTab} className="w-full">
                    <TabsList className={`grid w-full mb-4`} style={{ gridTemplateColumns: `repeat(${Math.min(sheets.length, 6)}, 1fr)` }}>
                        {sheets.map((sheet, idx) => (
                            <TabsTrigger
                                key={idx}
                                value={sheet.name}
                                className="flex items-center gap-2 text-xs sm:text-sm truncate"
                                title={sheet.name}
                            >
                                <FileSpreadsheet className="w-4 h-4 flex-shrink-0" />
                                <span className="truncate">{sheet.name}</span>
                            </TabsTrigger>
                        ))}
                    </TabsList>

                    {sheets.map((sheet, idx) => (
                        <TabsContent key={idx} value={sheet.name}>
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <FileSpreadsheet className="w-5 h-5 text-primary" />
                                        {sheet.name}
                                        {sheet.years?.length > 0 && (
                                            <Badge variant="outline" className="ml-2">
                                                {sheet.years.length} Columns
                                            </Badge>
                                        )}
                                        {sheet.rows?.length > 0 && (
                                            <Badge variant="secondary" className="ml-2">
                                                {sheet.rows.length} Rows
                                            </Badge>
                                        )}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <SheetTable data={sheet} />
                                </CardContent>
                            </Card>
                        </TabsContent>
                    ))}
                </Tabs>
            </div>
        );
    }

    // OLD FORMAT: Fixed 4 tabs (backward compatibility)
    const oldData = data as CMADataOld;

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
                            <GeneralInfoSection data={oldData.general_info || {}} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="operating">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FileSpreadsheet className="w-5 h-5 text-primary" />
                                Operating Statement
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <SheetTable data={oldData.operating_statement || { years: [], rows: [] }} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="balance">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Scale className="w-5 h-5 text-primary" />
                                Balance Sheet
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <SheetTable data={oldData.balance_sheet || { years: [], rows: [] }} />
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="cashflow">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Banknote className="w-5 h-5 text-primary" />
                                Cash Flow Statement
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <SheetTable data={oldData.cash_flow || { years: [], rows: [] }} />
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
