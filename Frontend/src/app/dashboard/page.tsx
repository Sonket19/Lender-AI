'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import type { AnalysisData } from '@/lib/types';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2, Download, Upload, Loader2, AlertTriangle, Zap, Search } from 'lucide-react';
import Header from '@/components/header';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogTrigger,
} from '@/components/ui/dialog';
import FileUpload from '@/components/file-upload';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { authenticatedFetch } from '@/lib/api-client';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export default function InvestorDashboard() {
  const [startups, setStartups] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const { toast } = useToast();
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/');
    }
  }, [user, authLoading, router]);

  const fetchDeals = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/deals`);
      if (!response.ok) {
        throw new Error('Failed to fetch deals. Please try again later.');
      }
      const data = await response.json();
      console.log(data.deals)
      setStartups(data.deals);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchDeals();
    }
  }, [fetchDeals, user]);

  const handleDelete = async (startupId: string) => {
    const originalStartups = [...startups];
    setStartups(currentStartups => currentStartups.filter(s => s.id !== startupId));
    try {
      const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/deals/${startupId}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to delete the analysis.');
      }
      toast({
        title: "Analysis Deleted",
        description: "The startup analysis has been successfully deleted.",
      });
    } catch (error: any) {
      setStartups(originalStartups);
      toast({
        variant: "destructive",
        title: "Deletion Failed",
        description: error.message || "An unexpected error occurred.",
      });
    }
  };

  const handleDownload = async (dealId: string, companyName: string) => {
    setDownloading(dealId);
    try {
      const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/download_memo/${dealId}`);
      if (!response.ok) {
        throw new Error('Download failed');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${companyName}-memo.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download memo", error);
      toast({
        variant: "destructive",
        title: "Download Failed",
        description: "Could not download the investment memo.",
      })
    } finally {
      setDownloading(null);
    }
  };

  const handleUploadComplete = () => {
    setIsUploadDialogOpen(false);
    fetchDeals();
  }

  const renderContent = () => {
    if (isLoading && startups.length === 0) {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="p-5 space-y-3 shadow-md">
              <div className="flex justify-between items-start gap-3">
                <div className="space-y-1.5 flex-1">
                  <Skeleton className="h-5 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-11 w-11 rounded-full" />
              </div>
              <Skeleton className="h-8 w-full rounded-md" />
              <div className="space-y-2.5">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-3 w-full" />
              </div>
              <div className="flex justify-between items-center pt-2 border-t">
                <Skeleton className="h-8 w-28" />
                <div className="flex gap-2">
                  <Skeleton className="h-8 w-8" />
                  <Skeleton className="h-8 w-8" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="destructive" className="mt-8">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Failed to Load Deals</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      );
    }

    if (startups.length > 0) {
      return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {startups.map(startup => {
            const memo = startup.memo?.draft_v1;
            const score = memo?.risk_metrics?.composite_risk_score || 0;
            const recommendation = memo?.conclusion?.overall_attractiveness || 'N/A';

            // Determine color based on score (Lower is better/safer usually, but let's assume 0-100 where higher might be riskier? 
            // Wait, previous context said "Safety Score" in table header but "Risk Score" in data. 
            // Let's assume standard risk score: Low is good.
            // < 30: Green (Safe), 30-60: Yellow (Moderate), > 60: Red (Risky)
            let scoreColor = "text-green-600 bg-green-50 border-green-200";
            if (score > 30) scoreColor = "text-yellow-600 bg-yellow-50 border-yellow-200";
            if (score > 60) scoreColor = "text-red-600 bg-red-50 border-red-200";

            return (
              <Card key={startup.id} className="flex flex-col hover:shadow-xl transition-all duration-300 border border-border shadow-md bg-card overflow-hidden group">
                <div className="p-5 flex-1 flex flex-col space-y-3">
                  <div className="flex justify-between items-start gap-3">
                    <Link href={`/startup/${startup.id}`} className="block group-hover:text-primary transition-colors flex-1 min-w-0">
                      <h3 className="font-headline font-bold text-lg line-clamp-1" title={startup.metadata.company_name}>
                        {startup.metadata.company_name}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">{startup.metadata.sector}</p>
                    </Link>
                    {/* Hide risk score for fast mode */}
                    {startup.metadata.processing_mode !== 'fast' && (
                      <div className={`flex flex-col items-center justify-center w-11 h-11 rounded-full border-2 ${scoreColor} shrink-0`}>
                        <span className="text-xs font-bold">{score}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {/* Processing Mode Badge */}
                      {startup.metadata.processing_mode === 'fast' ? (
                        <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-50 border border-orange-200">
                          <Zap className="w-3 h-3 text-orange-600" />
                          <span className="text-xs font-medium text-orange-700">Fast</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200">
                          <Search className="w-3 h-3 text-blue-600" />
                          <span className="text-xs font-medium text-blue-700">Research</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Hide recommendation for fast mode */}
                  {startup.metadata.processing_mode !== 'fast' && (
                    <div className="flex items-center justify-between text-sm py-1.5 px-2.5 rounded-md bg-secondary/50">
                      <span className="text-xs text-muted-foreground font-medium">Recommendation:</span>
                      <span className="font-semibold text-xs uppercase tracking-wide text-primary">
                        {recommendation}
                      </span>
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="18" height="18" x="3" y="4" rx="2" ry="2" />
                      <line x1="16" x2="16" y1="2" y2="6" />
                      <line x1="8" x2="8" y1="2" y2="6" />
                      <line x1="3" x2="21" y1="10" y2="10" />
                    </svg>
                    <span>
                      {new Date(startup.metadata.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>

                  <div className="space-y-2 pt-1">
                    {memo?.conclusion?.product_summary && (
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <div className="w-1 h-1 rounded-full bg-primary/60"></div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Product</span>
                        </div>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <p className={`text-xs text-foreground/80 leading-relaxed pl-2.5 cursor-help ${startup.metadata.processing_mode === 'fast' ? 'line-clamp-6' : 'line-clamp-2'
                                }`}>
                                {memo.conclusion.product_summary}
                              </p>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-md">
                              <p className="text-xs">{memo.conclusion.product_summary}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    )}

                    {memo?.conclusion?.financial_analysis && (
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <div className="w-1 h-1 rounded-full bg-primary/60"></div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Financials</span>
                        </div>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <p className={`text-xs text-foreground/80 leading-relaxed pl-2.5 cursor-help ${startup.metadata.processing_mode === 'fast' ? 'line-clamp-6' : 'line-clamp-2'
                                }`}>
                                {memo.conclusion.financial_analysis}
                              </p>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-md">
                              <p className="text-xs">{memo.conclusion.financial_analysis}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    )}

                    {/* Hide thesis for fast mode */}
                    {startup.metadata.processing_mode !== 'fast' && memo?.conclusion?.investment_thesis && (
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <div className="w-1 h-1 rounded-full bg-primary/60"></div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Thesis</span>
                        </div>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <p className="text-xs text-foreground/80 leading-relaxed line-clamp-2 pl-2.5 cursor-help">
                                {memo.conclusion.investment_thesis}
                              </p>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-md">
                              <p className="text-xs">{memo.conclusion.investment_thesis}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    )}

                    {/* Hide risk for fast mode */}
                    {startup.metadata.processing_mode !== 'fast' && memo?.conclusion?.risk_summary && (
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <div className="w-1 h-1 rounded-full bg-primary/60"></div>
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk</span>
                        </div>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <p className="text-xs text-foreground/80 leading-relaxed line-clamp-2 pl-2.5 cursor-help">
                                {memo.conclusion.risk_summary}
                              </p>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-md">
                              <p className="text-xs">{memo.conclusion.risk_summary}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    )}

                    {!memo?.conclusion?.product_summary && !memo?.conclusion?.financial_analysis &&
                      !memo?.conclusion?.investment_thesis && !memo?.conclusion?.risk_summary && (
                        <p className="text-xs text-muted-foreground italic">No conclusion data available.</p>
                      )}
                  </div>
                </div>

                <div className="p-4 bg-secondary/30 border-t border-border/50 flex items-center justify-between">
                  <Link href={`/startup/${startup.id}`} className="text-sm font-medium text-primary hover:underline">
                    View Analysis
                  </Link>
                  <div className="flex gap-2">
                    {memo && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-primary"
                        disabled={downloading === startup.id}
                        onClick={() => handleDownload(startup.id, startup.metadata.company_name)}
                        title="Download Word Doc"
                      >
                        {downloading === startup.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" title="Delete Analysis">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete Analysis?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently remove the analysis for <span className="font-bold">{startup.metadata.company_name}</span>.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => handleDelete(startup.id)} className="bg-destructive hover:bg-destructive/90">Delete</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      );
    }

    return (
      <div className="text-center py-20 border-2 border-dashed rounded-xl bg-secondary/20">
        <div className="bg-background p-4 rounded-full inline-flex mb-4 shadow-sm">
          <Upload className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="text-2xl font-headline font-semibold">No Startups Analyzed</h2>
        <p className="text-muted-foreground mt-2 max-w-md mx-auto">Upload a pitch deck to generate your first comprehensive investment analysis.</p>
        <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
          <DialogTrigger asChild>
            <Button className="mt-6" size="lg">
              <Upload className="mr-2 h-4 w-4" />
              Analyze New Startup
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-xl">
            <FileUpload onGenerate={handleUploadComplete} />
          </DialogContent>
        </Dialog>
      </div>
    );
  };

  if (authLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8 md:py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-headline font-bold">Investor Dashboard</h1>
            <p className="text-muted-foreground">Your portfolio of analyzed startups.</p>
          </div>
          {startups.length > 0 && (
            <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Document
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-xl">
                <FileUpload onGenerate={handleUploadComplete} />
              </DialogContent>
            </Dialog>
          )}
        </div>

        {renderContent()}
      </main>
    </div>
  );
}
