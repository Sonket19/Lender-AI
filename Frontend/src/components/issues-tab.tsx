
'use client';

import { useState, useEffect } from 'react';
import type { InterviewIssue } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { AlertTriangle, CalendarPlus, RotateCcw, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { authenticatedFetch } from '@/lib/api-client';

const getImportanceColor = (importance: string) => {
    switch (importance.toLowerCase()) {
        case 'critical': return 'bg-destructive/80 text-destructive-foreground';
        case 'high': return 'bg-yellow-500 text-white';
        case 'medium': return 'bg-blue-500 text-white';
        default: return 'bg-gray-400 text-white';
    }
}

type IssuesTabProps = {
    issues: InterviewIssue[];
    onSelectionChange?: (selectedFields: string[]) => void;
    dealId: string;
    defaultFounderName?: string;
    interviewStatus?: string;
    onInterviewReset?: () => void;
};

export default function IssuesTab({
    issues,
    onSelectionChange,
    dealId,
    defaultFounderName = '',
    interviewStatus,
    onInterviewReset
}: IssuesTabProps) {
    const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set());
    const [isMeetingDialogOpen, setIsMeetingDialogOpen] = useState(false);
    const [founderName, setFounderName] = useState(defaultFounderName);
    const [founderEmail, setFounderEmail] = useState('');
    const [isSettingMeeting, setIsSettingMeeting] = useState(false);
    const [isResetting, setIsResetting] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const { toast } = useToast();

    // Initialize with all issues selected
    useEffect(() => {
        if (issues && issues.length > 0) {
            const allFields = new Set(issues.map(issue => issue.field));
            setSelectedFields(allFields);
            onSelectionChange?.(Array.from(allFields));
        }
    }, [issues]);

    useEffect(() => {
        if (defaultFounderName) {
            setFounderName(defaultFounderName);
        }
    }, [defaultFounderName]);

    const handleToggleIssue = (field: string) => {
        const newSelected = new Set(selectedFields);
        if (newSelected.has(field)) {
            newSelected.delete(field);
        } else {
            newSelected.add(field);
        }
        setSelectedFields(newSelected);
        onSelectionChange?.(Array.from(newSelected));
    };

    const handleToggleAll = () => {
        if (selectedFields.size === issues.length) {
            // Deselect all
            setSelectedFields(new Set());
            onSelectionChange?.([]);
        } else {
            // Select all
            const allFields = new Set(issues.map(issue => issue.field));
            setSelectedFields(allFields);
            onSelectionChange?.(Array.from(allFields));
        }
    };

    const handleSetMeeting = async () => {
        if (selectedFields.size === 0) {
            toast({
                variant: 'destructive',
                title: 'No Questions Selected',
                description: 'Please select at least one question for the interview.',
            });
            return;
        }

        setIsSettingMeeting(true);
        try {
            const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/interviews/initiate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    deal_id: dealId,
                    founder_email: founderEmail,
                    founder_name: founderName,
                    selected_fields: Array.from(selectedFields)
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to send interview invitation.');
            }

            if (result.success === false) {
                throw new Error(result.detail || 'Failed to send interview invitation.');
            }

            toast({
                title: 'Invitation Sent',
                description: `An interview invitation with ${selectedFields.size} questions has been sent to ${founderName}.`,
            });
            setIsMeetingDialogOpen(false);
            setFounderEmail('');

        } catch (error: any) {
            toast({
                variant: 'destructive',
                title: 'Failed to Set Meeting',
                description: error.message || 'An unexpected error occurred.',
            });
        } finally {
            setIsSettingMeeting(false);
        }
    };

    const handleResetInterview = async () => {
        setIsResetting(true);
        try {
            const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/interviews/reset/${dealId}`, {
                method: 'DELETE',
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to reset interview.');
            }

            toast({
                title: 'Interview Reset',
                description: 'The interview has been reset. You can now start a new one.',
            });

            // Trigger parent refresh
            onInterviewReset?.();

        } catch (error: any) {
            toast({
                variant: 'destructive',
                title: 'Failed to Reset',
                description: error.message || 'An unexpected error occurred.',
            });
        } finally {
            setIsResetting(false);
        }
    };

    const handleGenerateQuestions = async () => {
        setIsGenerating(true);
        try {
            const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/interviews/generate/${dealId}`, {
                method: 'POST',
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to generate questions.');
            }

            toast({
                title: 'Questions Generated',
                description: result.message,
            });

            // Trigger parent refresh to load the new questions
            onInterviewReset?.();

        } catch (error: any) {
            toast({
                variant: 'destructive',
                title: 'Failed to Generate Questions',
                description: error.message || 'An unexpected error occurred.',
            });
        } finally {
            setIsGenerating(false);
        }
    };

    if (!issues || issues.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="font-headline text-2xl flex items-center gap-3">
                        <AlertTriangle className="w-7 h-7 text-primary" />
                        Interview Questions
                    </CardTitle>
                    <CardDescription>
                        Generate interview questions based on gaps identified in the investment memo.
                    </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col items-center justify-center py-10">
                    <div className="text-center space-y-4">
                        <p className="text-muted-foreground">
                            No interview questions have been generated yet.
                        </p>
                        <Button
                            onClick={handleGenerateQuestions}
                            disabled={isGenerating}
                            size="lg"
                        >
                            {isGenerating ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Analyzing memo...
                                </>
                            ) : (
                                <>
                                    <CalendarPlus className="mr-2 h-4 w-4" />
                                    Generate Interview Questions
                                </>
                            )}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const allSelected = selectedFields.size === issues.length;
    const someSelected = selectedFields.size > 0 && selectedFields.size < issues.length;
    const isInterviewActive = interviewStatus === 'active' || interviewStatus === 'pending';

    return (
        <>
            <Card>
                <CardHeader>
                    <div className="flex items-start justify-between">
                        <div>
                            <CardTitle className="font-headline text-2xl flex items-center gap-3">
                                <AlertTriangle className="w-7 h-7 text-primary" />
                                Identified Issues for Founder Interview
                            </CardTitle>
                            <CardDescription className="mt-2">
                                Select the questions you want to include in the interview. {selectedFields.size} of {issues.length} questions selected.
                            </CardDescription>
                        </div>
                        {isInterviewActive && (
                            <Badge variant="outline" className="bg-yellow-500/10 text-yellow-600 border-yellow-500/30">
                                Interview {interviewStatus}
                            </Badge>
                        )}
                    </div>
                </CardHeader>
                <CardContent>
                    {/* Select All Toggle */}
                    <div
                        className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-primary/10 border border-primary/20 cursor-pointer hover:bg-primary/15 transition-colors"
                        onClick={handleToggleAll}
                    >
                        <Checkbox
                            id="select-all"
                            checked={allSelected}
                            // @ts-ignore - indeterminate is a valid DOM property
                            data-state={someSelected ? "indeterminate" : allSelected ? "checked" : "unchecked"}
                            onCheckedChange={handleToggleAll}
                            className="data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                        />
                        <label htmlFor="select-all" className="text-sm font-medium cursor-pointer flex-1">
                            {allSelected ? 'Deselect All' : 'Select All'} ({issues.length} questions)
                        </label>
                    </div>

                    <div className="max-h-[45vh] overflow-y-auto pr-2 space-y-2">
                        {issues.map((issue, index) => (
                            <div
                                key={index}
                                className={`flex items-center gap-3 text-sm p-3 rounded-lg cursor-pointer transition-colors ${selectedFields.has(issue.field)
                                    ? 'bg-secondary/70 border border-primary/30'
                                    : 'bg-secondary/30 border border-transparent hover:bg-secondary/50'
                                    }`}
                                onClick={() => handleToggleIssue(issue.field)}
                            >
                                <Checkbox
                                    id={`issue-${index}`}
                                    checked={selectedFields.has(issue.field)}
                                    onCheckedChange={() => handleToggleIssue(issue.field)}
                                    className="data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                                />
                                <span className="flex-1 pr-2">{issue.question}</span>
                                <div className="flex gap-2 items-center">
                                    <Badge variant="secondary" className="capitalize">{issue.category}</Badge>
                                    <Badge className={`${getImportanceColor(issue.importance)} capitalize`}>{issue.importance}</Badge>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
                <CardFooter className="flex justify-end gap-3 border-t pt-6">
                    {isInterviewActive && (
                        <Button
                            variant="outline"
                            onClick={handleResetInterview}
                            disabled={isResetting}
                            className="text-destructive border-destructive/30 hover:bg-destructive/10"
                        >
                            {isResetting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RotateCcw className="mr-2 h-4 w-4" />}
                            Reset Interview
                        </Button>
                    )}
                    <Button
                        onClick={() => setIsMeetingDialogOpen(true)}
                        disabled={selectedFields.size === 0}
                    >
                        <CalendarPlus className="mr-2 h-4 w-4" />
                        Set Meeting ({selectedFields.size} questions)
                    </Button>
                </CardFooter>
            </Card>

            {/* Set Meeting Dialog */}
            <Dialog open={isMeetingDialogOpen} onOpenChange={setIsMeetingDialogOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle className="font-headline text-2xl flex items-center gap-3">
                            <CalendarPlus className="w-7 h-7 text-primary" />
                            Set Up Interview
                        </DialogTitle>
                        <DialogDescription>
                            Send an interview invitation with {selectedFields.size} selected questions.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="name" className="text-right">
                                Name
                            </Label>
                            <Input
                                id="name"
                                value={founderName}
                                onChange={(e) => setFounderName(e.target.value)}
                                className="col-span-3"
                            />
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="email" className="text-right">
                                Email
                            </Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="founder@example.com"
                                value={founderEmail}
                                onChange={(e) => setFounderEmail(e.target.value)}
                                className="col-span-3"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button onClick={handleSetMeeting} disabled={isSettingMeeting || !founderName || !founderEmail}>
                            {isSettingMeeting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            Send Invitation
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    )
}

