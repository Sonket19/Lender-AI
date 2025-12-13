
'use client';

import type { InterviewIssue } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle } from 'lucide-react';

const getImportanceColor = (importance: string) => {
    switch (importance.toLowerCase()) {
        case 'critical': return 'bg-destructive/80 text-destructive-foreground';
        case 'high': return 'bg-yellow-500 text-white';
        case 'medium': return 'bg-blue-500 text-white';
        default: return 'bg-gray-400 text-white';
    }
}

export default function IssuesTab({ issues }: { issues: InterviewIssue[] }) {
    if (!issues || issues.length === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="font-headline text-2xl flex items-center gap-3"><AlertTriangle className="w-7 h-7 text-primary" />Identified Issues</CardTitle>
                    <CardDescription>
                        No outstanding issues were identified during the analysis.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">All clear!</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="font-headline text-2xl flex items-center gap-3"><AlertTriangle className="w-7 h-7 text-primary" />Identified Issues for Founder Interview</CardTitle>
                <CardDescription>
                    The following {issues.length} issues were identified during analysis and require clarification. Use the "Set Meeting" feature to initiate an interview.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <div className="max-h-[60vh] overflow-y-auto pr-2 space-y-2">
                    {issues.map((issue, index) => (
                        <div key={index} className="flex items-center justify-between text-sm p-3 rounded-lg bg-secondary/50">
                            <span className="flex-1 pr-2">{issue.question}</span>
                            <div className="flex gap-2 items-center">
                                <Badge variant="secondary" className="capitalize">{issue.category}</Badge>
                                <Badge className={`${getImportanceColor(issue.importance)} capitalize`}>{issue.importance}</Badge>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}
