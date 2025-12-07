'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Loader2, Mail, ArrowRight, CheckCircle2 } from 'lucide-react';
import { auth, googleProvider } from '@/lib/firebase';
import { signInWithPopup, signInWithCustomToken } from 'firebase/auth';
import { useToast } from '@/hooks/use-toast';

interface AuthModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function AuthModal({ isOpen, onClose }: AuthModalProps) {
    const [email, setEmail] = useState('');
    const [code, setCode] = useState('');
    const [step, setStep] = useState<'email' | 'code'>('email');
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();
    const { toast } = useToast();

    const handleGoogleLogin = async () => {
        setIsLoading(true);
        try {
            const result = await signInWithPopup(auth, googleProvider);
            const user = result.user;

            // Sync with backend
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/google-login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: user.email,
                    uid: user.uid,
                    name: user.displayName,
                    photo_url: user.photoURL
                })
            });

            if (!response.ok) throw new Error('Backend sync failed');

            toast({
                title: "Welcome back!",
                description: `Signed in as ${user.email}`,
            });

            // router.push('/dashboard'); // Let the LandingPage redirect
            onClose();
        } catch (error: any) {
            console.error(error);
            toast({
                variant: "destructive",
                title: "Login Failed",
                description: error.message || "Could not sign in with Google",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleSendCode = async () => {
        if (!email) return;
        setIsLoading(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/send-code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });

            if (!response.ok) throw new Error('Failed to send code');

            setStep('code');
            toast({
                title: "Code Sent",
                description: "Check your email for the verification code.",
            });
        } catch (error: any) {
            toast({
                variant: "destructive",
                title: "Error",
                description: error.message || "Could not send verification code",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleVerifyCode = async () => {
        if (!code) return;
        setIsLoading(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/verify-code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, code })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Verification failed');
            }

            const data = await response.json();

            // Sign in with the custom token from the backend
            if (data.custom_token) {
                await signInWithCustomToken(auth, data.custom_token);
            } else {
                throw new Error('No auth token received from server');
            }

            toast({
                title: "Success",
                description: "Email verified successfully!",
            });

            // router.push('/dashboard'); // Let the LandingPage redirect
            onClose();
        } catch (error: any) {
            toast({
                variant: "destructive",
                title: "Verification Failed",
                description: error.message,
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="text-2xl font-headline text-center">
                        {step === 'email' ? 'Get Started' : 'Verify Email'}
                    </DialogTitle>
                    <DialogDescription className="text-center">
                        {step === 'email'
                            ? 'Sign in to access your AI investment analyst.'
                            : `Enter the code sent to ${email}`}
                    </DialogDescription>
                </DialogHeader>

                <div className="flex flex-col gap-4 py-4">
                    {step === 'email' ? (
                        <>
                            <Button
                                variant="outline"
                                className="w-full h-12 text-base relative"
                                onClick={handleGoogleLogin}
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                                        <path
                                            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                            fill="#4285F4"
                                        />
                                        <path
                                            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                            fill="#34A853"
                                        />
                                        <path
                                            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                                            fill="#FBBC05"
                                        />
                                        <path
                                            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                                            fill="#EA4335"
                                        />
                                    </svg>
                                )}
                                Continue with Google
                            </Button>

                            <div className="relative">
                                <div className="absolute inset-0 flex items-center">
                                    <span className="w-full border-t" />
                                </div>
                                <div className="relative flex justify-center text-xs uppercase">
                                    <span className="bg-background px-2 text-muted-foreground">
                                        Or continue with email
                                    </span>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Input
                                    type="email"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    disabled={isLoading}
                                    className="h-11"
                                />
                                <Button
                                    className="w-full h-11"
                                    onClick={handleSendCode}
                                    disabled={isLoading || !email}
                                >
                                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4 mr-2" />}
                                    Send Verification Code
                                </Button>
                            </div>
                        </>
                    ) : (
                        <div className="space-y-4">
                            <div className="flex justify-center">
                                <div className="bg-primary/10 p-3 rounded-full">
                                    <Mail className="w-8 h-8 text-primary" />
                                </div>
                            </div>
                            <Input
                                type="text"
                                placeholder="Enter 6-digit code"
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                className="text-center text-2xl tracking-widest h-14 font-mono"
                                disabled={isLoading}
                            />
                            <Button
                                className="w-full h-11"
                                onClick={handleVerifyCode}
                                disabled={isLoading || code.length !== 6}
                            >
                                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
                                Verify & Sign In
                            </Button>
                            <Button
                                variant="ghost"
                                className="w-full"
                                onClick={() => setStep('email')}
                                disabled={isLoading}
                            >
                                Change Email
                            </Button>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
