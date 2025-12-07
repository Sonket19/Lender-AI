'use client';

import { useState, useEffect, useRef } from 'react';
import type { AnalysisData } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Loader2, Send, User, Bot, Trash2 } from 'lucide-react';
import { ScrollArea } from './ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { authenticatedFetch } from '@/lib/api-client';

type Message = {
  role: 'user' | 'model';
  content: string;
};

interface ChatbotProps {
  analysisData: AnalysisData;
  onClearChat?: () => void;
}

export default function Chatbot({ analysisData, onClearChat }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const dealId = analysisData.metadata.deal_id;

  // Load chat history from localStorage on mount
  useEffect(() => {
    const storageKey = `chat_history_${dealId}`;
    const savedMessages = localStorage.getItem(storageKey);

    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (e) {
        console.error('Failed to parse saved messages', e);
        // Initialize with greeting if parse fails
        initializeChat();
      }
    } else {
      // Initialize with greeting if no saved messages
      initializeChat();
    }
  }, [dealId]);

  // Save chat history to localStorage whenever messages change
  useEffect(() => {
    if (messages.length > 0) {
      const storageKey = `chat_history_${dealId}`;
      localStorage.setItem(storageKey, JSON.stringify(messages));
    }
  }, [messages, dealId]);

  const initializeChat = () => {
    setMessages([
      {
        role: 'model',
        content: `Hello! I've analyzed the pitch deck for **${analysisData.metadata.company_name}**. I can answer questions about their business model, market, team, or financials based on the deck and my research. What would you like to know?`
      }
    ]);
  };

  const clearChat = () => {
    const storageKey = `chat_history_${dealId}`;
    localStorage.removeItem(storageKey);
    initializeChat();
    if (onClearChat) onClearChat();
  };

  useEffect(() => {
    if (scrollAreaRef.current) {
      const viewport = scrollAreaRef.current.querySelector('div[data-radix-scroll-area-viewport]');
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    const newMessages: Message[] = [...messages, userMessage];
    setMessages(newMessages);

    // Save user message immediately
    const storageKey = `chat_history_${dealId}`;
    localStorage.setItem(storageKey, JSON.stringify(newMessages));

    setInput('');
    setIsLoading(true);

    try {
      const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/investor_chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          deal_id: analysisData.metadata.deal_id,
          message: input,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      const updatedMessages = [...newMessages, { role: 'model', content: data.message }];

      // Save AI response immediately to localStorage
      localStorage.setItem(storageKey, JSON.stringify(updatedMessages));
      setMessages(updatedMessages);
    } catch (e) {
      console.error(e);
      const errorMessages = [...newMessages, { role: 'model', content: 'Sorry, I encountered an error. Please try again.' }];

      // Save error message immediately to localStorage
      localStorage.setItem(storageKey, JSON.stringify(errorMessages));
      setMessages(errorMessages);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-4 overflow-hidden p-4">
        <ScrollArea className="flex-1 pr-4" ref={scrollAreaRef}>
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex items-start gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
              >
                {message.role === 'model' && (
                  <div className="bg-primary p-2 rounded-full text-primary-foreground flex-shrink-0">
                    <Bot size={20} />
                  </div>
                )}
                <div
                  className={`max-w-[75%] rounded-lg p-4 ${message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
                    }`}
                >
                  {message.role === 'model' ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-muted-foreground prose-p:text-muted-foreground prose-strong:text-muted-foreground prose-li:text-muted-foreground">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-base leading-relaxed">{message.content}</p>
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="bg-primary p-2 rounded-full text-primary-foreground flex-shrink-0">
                    <User size={20} />
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
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
        <div className="flex items-center gap-2 pt-3 border-t mt-auto">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSendMessage()}
            placeholder="Ask me anything about this startup..."
            disabled={isLoading}
          />
          <Button onClick={handleSendMessage} disabled={isLoading || !input.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </CardContent>
    </Card >
  );
}
