import React, { useState } from 'react';
import { MessageCircle, X, Minimize2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Chatbot from './chatbot';
import { AnalysisData } from '@/lib/types';

interface FloatingChatProps {
    analysisData: AnalysisData;
}

export default function FloatingChat({ analysisData }: FloatingChatProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isMinimized, setIsMinimized] = useState(false);
    const [chatKey, setChatKey] = useState(0);

    const handleClearChat = () => {
        // Clear localStorage first
        const dealId = analysisData.metadata.deal_id;
        const storageKey = `chat_history_${dealId}`;
        localStorage.removeItem(storageKey);
        // Then remount component with fresh state
        setChatKey(prev => prev + 1);
    };

    return (
        <>
            {/* Floating Chat Window */}
            {isOpen && !isMinimized && (
                <div className="fixed bottom-12 right-6 w-[480px] h-[600px] bg-background border-2 border-border rounded-lg shadow-2xl z-50 flex flex-col">
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 border-b bg-muted/30">
                        <div className="flex items-center gap-2">
                            <MessageCircle className="w-5 h-5 text-primary" />
                            <h3 className="font-semibold">AI Assistant</h3>
                        </div>
                        <div className="flex items-center gap-1">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={handleClearChat}
                                title="Clear chat history"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /></svg>
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => setIsMinimized(true)}
                            >
                                <Minimize2 className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={() => setIsOpen(false)}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>

                    {/* Chat Content */}
                    <div className="flex-1 overflow-hidden">
                        <Chatbot key={chatKey} analysisData={analysisData} onClearChat={handleClearChat} />
                    </div>
                </div>
            )}

            {/* Minimized State */}
            {isOpen && isMinimized && (
                <div className="fixed bottom-24 right-6 bg-background border-2 border-border rounded-lg shadow-xl z-50 p-3">
                    <div className="flex items-center gap-3">
                        <MessageCircle className="w-5 h-5 text-primary" />
                        <span className="font-medium">AI Assistant</span>
                        <div className="flex items-center gap-1 ml-2">
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => setIsMinimized(false)}
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <polyline points="15 3 21 3 21 9"></polyline>
                                    <polyline points="9 21 3 21 3 15"></polyline>
                                    <line x1="21" y1="3" x2="14" y2="10"></line>
                                    <line x1="3" y1="21" x2="10" y2="14"></line>
                                </svg>
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => setIsOpen(false)}
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Floating Button */}
            {!isOpen && (
                <Button
                    onClick={() => {
                        setIsOpen(true);
                        setIsMinimized(false);
                    }}
                    size="icon"
                    className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg hover:scale-110 transition-transform z-50"
                >
                    <MessageCircle className="h-6 w-6" />
                </Button>
            )}
        </>
    );
}
