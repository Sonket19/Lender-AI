'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ArrowRight, BarChart3, ShieldCheck, Zap } from 'lucide-react';
import AuthModal from '@/components/auth-modal';
import Link from 'next/link';
import { useAuth } from '@/components/auth-provider';
import { useRouter } from 'next/navigation';

export default function LandingPage() {
    const [isAuthOpen, setIsAuthOpen] = useState(false);
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && user) {
            router.push('/dashboard');
        }
    }, [user, loading, router]);

    if (loading) return null; // Or a loading spinner

    return (
        <div className="min-h-screen bg-background flex flex-col">
            {/* Header */}
            <header className="border-b">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="bg-primary text-primary-foreground p-1.5 rounded-lg">
                            <Zap size={20} fill="currentColor" />
                        </div>
                        <span className="font-headline font-bold text-xl tracking-tight">PitchLens</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Button variant="ghost" onClick={() => setIsAuthOpen(true)}>Sign In</Button>
                        <Button onClick={() => setIsAuthOpen(true)}>Get Started</Button>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <main className="flex-1">
                <section className="py-20 md:py-32">
                    <div className="container mx-auto px-4 text-center max-w-4xl">
                        <div className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-primary/10 text-primary hover:bg-primary/20 mb-8">
                            New: AI-Powered Interview Mode
                        </div>
                        <h1 className="text-4xl md:text-6xl font-headline font-bold tracking-tight mb-6">
                            Investment Memos in <span className="text-primary">Minutes</span>, Not Days.
                        </h1>
                        <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
                            Upload a pitch deck and get a comprehensive investment memo, risk analysis, and automated founder interview questions instantly.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Button size="lg" className="h-12 px-8 text-lg" onClick={() => setIsAuthOpen(true)}>
                                Analyze a Startup <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                            <Button size="lg" variant="outline" className="h-12 px-8 text-lg">
                                View Sample Memo
                            </Button>
                        </div>
                    </div>
                </section>

                {/* Features Grid */}
                <section className="py-20 bg-secondary/30">
                    <div className="container mx-auto px-4">
                        <div className="grid md:grid-cols-3 gap-8">
                            <div className="bg-background p-8 rounded-xl border shadow-sm">
                                <div className="bg-primary/10 w-12 h-12 rounded-lg flex items-center justify-center mb-6">
                                    <BarChart3 className="text-primary h-6 w-6" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Deep Analysis</h3>
                                <p className="text-muted-foreground">
                                    Our AI extracts key metrics, validates market size, and identifies red flags in seconds.
                                </p>
                            </div>
                            <div className="bg-background p-8 rounded-xl border shadow-sm">
                                <div className="bg-primary/10 w-12 h-12 rounded-lg flex items-center justify-center mb-6">
                                    <ShieldCheck className="text-primary h-6 w-6" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Risk Assessment</h3>
                                <p className="text-muted-foreground">
                                    Get a calculated risk score based on team, market, traction, and financial health.
                                </p>
                            </div>
                            <div className="bg-background p-8 rounded-xl border shadow-sm">
                                <div className="bg-primary/10 w-12 h-12 rounded-lg flex items-center justify-center mb-6">
                                    <Zap className="text-primary h-6 w-6" />
                                </div>
                                <h3 className="text-xl font-bold mb-3">Automated Interviews</h3>
                                <p className="text-muted-foreground">
                                    AI generates specific questions for missing info and conducts the interview for you.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            {/* Footer */}
            <footer className="border-t py-12 bg-muted/30">
                <div className="container mx-auto px-4 text-center text-muted-foreground">
                    <p>&copy; 2024 PitchLens. All rights reserved.</p>
                </div>
            </footer>

            <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />
        </div>
    );
}
