
'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, notFound } from 'next/navigation';
import { Loader2, Send, User, Bot, AlertTriangle } from 'lucide-react';
import Header from '@/components/header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import type { ValidationResponse, ChatMessage } from '@/lib/types';
import { useToast } from '@/hooks/use-toast';

export default function InterviewPage() {
  const params = useParams();
  const token = params.token as string;
  const [validationData, setValidationData] = useState<ValidationResponse | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    const validateToken = async () => {
      if (!token) return;
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/interviews/validate/${token}`);
        if (!response.ok) {
          if (response.status === 404 || response.status === 403) {
             const errorData = await response.json();
             throw new Error(errorData.detail || 'This interview link is invalid or has expired.');
          }
          throw new Error('Failed to validate the interview session.');
        }
        const data: ValidationResponse = await response.json();
        if (!data.valid) {
          throw new Error('This interview link is invalid or has expired.');
        }
        setValidationData(data);
        setMessages(data.chat_history);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    validateToken();
  }, [token]);

  useEffect(() => {
    if (scrollAreaRef.current) {
        const viewport = scrollAreaRef.current.querySelector('div[data-radix-scroll-area-viewport]');
        if (viewport) {
            viewport.scrollTop = viewport.scrollHeight;
        }
    }
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim() || !token) return;

    const userMessage: ChatMessage = { role: 'user', message: input, timestamp: new Date().toISOString() };
    const newMessages: ChatMessage[] = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setIsSending(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/interviews/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          interview_token: token,
          message: input,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to get a response.');
      }
      
      const assistantMessage: ChatMessage = { role: 'assistant', message: result.message, timestamp: new Date().toISOString() };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (e: any) {
      toast({
        variant: "destructive",
        title: "Error",
        description: e.message,
      });
      // Revert user message on error
      setMessages(messages);
    } finally {
      setIsSending(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 container mx-auto px-4 py-8 md:py-12 flex items-center justify-center">
            <div className="flex flex-col items-center justify-center text-center">
                <Loader2 className="w-16 h-16 animate-spin text-primary mb-4" />
                <h2 className="text-2xl font-headline font-semibold text-primary">Validating Interview...</h2>
                <p className="text-muted-foreground mt-2">Please wait a moment.</p>
            </div>
        </main>
      </div>
    );
  }

  if (error) {
     return (
        <div className="flex flex-col min-h-screen">
            <Header />
            <main className="flex-1 container mx-auto px-4 py-8 md:py-12 flex items-center justify-center">
                 <Alert variant="destructive" className="max-w-lg">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Validation Failed</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            </main>
        </div>
     )
  }

  if (!validationData) {
    return notFound();
  }
  
  const { company_name, sector, founder_name, missing_fields_count } = validationData;

  return (
    <div className="flex flex-col min-h-screen bg-secondary/50">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8 md:py-12 flex items-start justify-center">
        <Card className="w-full max-w-3xl h-[80vh] flex flex-col shadow-2xl">
          <CardHeader className="border-b">
            <CardTitle className="font-headline text-2xl">Interview for {company_name}</CardTitle>
            <CardDescription>
                Welcome, {founder_name}. This is an automated interview to clarify details about {company_name} ({sector}).
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden pt-6">
            <ScrollArea className="flex-1 pr-4 -mr-4" ref={scrollAreaRef}>
              <div className="space-y-6">
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
                  >
                    {msg.role !== 'user' && (
                      <div className="bg-primary p-2 rounded-full text-primary-foreground">
                        <Bot size={20} />
                      </div>
                    )}
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-3 ${
                        msg.role === 'user'
                          ? 'bg-accent/80 text-accent-foreground'
                          : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{msg.message}</p>
                    </div>
                    {msg.role === 'user' && (
                        <div className="bg-accent p-2 rounded-full text-accent-foreground">
                            <User size={20} />
                        </div>
                    )}
                  </div>
                ))}
                 {isSending && (
                    <div className="flex items-start gap-3">
                        <div className="bg-primary p-2 rounded-full text-primary-foreground">
                        <Bot size={20} />
                        </div>
                        <div className="bg-muted text-muted-foreground rounded-lg p-3 flex items-center space-x-2">
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>Thinking...</span>
                        </div>
                    </div>
                )}
              </div>
            </ScrollArea>
            <div className="flex items-center gap-2 pt-4 border-t">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isSending && handleSendMessage()}
                placeholder="Type your answer..."
                disabled={isSending || validationData.status !== 'active'}
              />
              <Button onClick={handleSendMessage} disabled={isSending || !input.trim() || validationData.status !== 'active'}>
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
