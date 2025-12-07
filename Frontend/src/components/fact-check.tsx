import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle, ExternalLink, Loader2, ShieldCheck } from "lucide-react";
import { authenticatedFetch } from '@/lib/api-client';

interface FactCheckClaim {
    claim: string;
    verdict: 'Verified' | 'Exaggerated' | 'False' | 'Unverifiable';
    explanation: string;
    source_url?: string;
    confidence: 'High' | 'Medium' | 'Low';
}

interface FactCheckProps {
    dealId: string;
    existingData?: {
        claims: FactCheckClaim[];
        checked_at: string;
    };
}

export function FactCheck({ dealId, existingData }: FactCheckProps) {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<{ claims: FactCheckClaim[], checked_at: string } | null>(existingData || null);
    const [error, setError] = useState<string | null>(null);

    const runFactCheck = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/deals/${dealId}/fact-check`, {
                method: 'POST',
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to run fact check');
            }

            const result = await response.json();
            setData(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    const getVerdictBadge = (verdict: string) => {
        switch (verdict) {
            case 'Verified':
                return <Badge className="bg-green-500 hover:bg-green-600"><CheckCircle2 className="w-3 h-3 mr-1" /> Verified</Badge>;
            case 'Exaggerated':
                return <Badge className="bg-yellow-500 hover:bg-yellow-600"><AlertTriangle className="w-3 h-3 mr-1" /> Exaggerated</Badge>;
            case 'False':
                return <Badge className="bg-red-500 hover:bg-red-600"><XCircle className="w-3 h-3 mr-1" /> False</Badge>;
            default:
                return <Badge variant="secondary"><HelpCircle className="w-3 h-3 mr-1" /> Unverifiable</Badge>;
        }
    };

    if (!data && !loading) {
        return (
            <Card className="border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-10 text-center">
                    <ShieldCheck className="w-12 h-12 text-muted-foreground mb-4" />
                    <h3 className="text-lg font-semibold mb-2">Automated Fact Checking</h3>
                    <p className="text-sm text-muted-foreground max-w-md mb-6">
                        Run a deep-dive verification on key claims in this pitch deck using Google Search.
                        This process takes about 30-60 seconds.
                    </p>
                    <Button onClick={runFactCheck}>
                        Run Fact Check
                    </Button>
                    {error && <p className="text-red-500 text-sm mt-4">{error}</p>}
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5" />
                        Fact Check Report
                    </h3>
                    {data && (
                        <p className="text-xs text-muted-foreground">
                            Last checked: {new Date(data.checked_at).toLocaleString()}
                        </p>
                    )}
                </div>
                <Button variant="outline" size="sm" onClick={runFactCheck} disabled={loading}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    {loading ? 'Checking...' : 'Re-run Check'}
                </Button>
            </div>

            {error && (
                <div className="p-4 bg-red-50 text-red-600 rounded-md text-sm">
                    {error}
                </div>
            )}

            {loading && !data && (
                <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
                    <p className="text-sm text-muted-foreground">Verifying claims with Google Search...</p>
                </div>
            )}

            {data && (
                <div className="grid gap-4">
                    {data.claims.map((item, index) => (
                        <Card key={index} className="overflow-hidden">
                            <CardHeader className="pb-2 bg-muted/30">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            {getVerdictBadge(item.verdict)}
                                            <span className="text-xs text-muted-foreground border px-2 py-0.5 rounded-full">
                                                {item.confidence} Confidence
                                            </span>
                                        </div>
                                        <CardTitle className="text-base font-medium leading-relaxed">
                                            "{item.claim}"
                                        </CardTitle>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="pt-4">
                                <p className="text-sm text-muted-foreground mb-3">
                                    {item.explanation}
                                </p>
                                {item.source_url && (
                                    <a
                                        href={item.source_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs flex items-center text-blue-600 hover:underline"
                                    >
                                        <ExternalLink className="w-3 h-3 mr-1" />
                                        Source: {new URL(item.source_url).hostname}
                                    </a>
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
