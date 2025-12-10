import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { UploadCloud, FileText, Video, Mic, Type, File, Loader2, Zap, Search } from 'lucide-react';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { useToast } from '@/hooks/use-toast';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { authenticatedFetch } from '@/lib/api-client';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type FileUploadProps = {
    onGenerate: () => void;
};

const FileInput = ({
    id,
    label,
    icon,
    file,
    onFileChange,
    accept,
}: {
    id: string;
    label: string;
    icon: React.ReactNode;
    file: File | null;
    onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
    accept: string;
}) => (
    <div className="space-y-4 py-4">
        <div className="flex flex-col items-center justify-center border-2 border-dashed border-muted-foreground/25 rounded-lg p-10 hover:bg-muted/50 transition-colors">
            <div className="bg-primary/10 p-4 rounded-full mb-4">
                {icon}
            </div>
            <h3 className="text-lg font-semibold mb-1">{label}</h3>
            <p className="text-sm text-muted-foreground mb-6 text-center max-w-xs">
                Drag and drop your file here, or click to browse
            </p>

            <div className="relative">
                <Input
                    id={id}
                    type="file"
                    className="sr-only"
                    onChange={onFileChange}
                    accept={accept}
                />
                <Label
                    htmlFor={id}
                    className="cursor-pointer inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
                >
                    Select File
                </Label>
            </div>

            {file && (
                <div className="mt-6 flex items-center gap-3 bg-secondary/50 p-3 rounded-md w-full max-w-md border">
                    <File className="w-5 h-5 text-primary" />
                    <span className="text-sm font-medium truncate flex-1">{file.name}</span>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                            e.preventDefault();
                            // This is a bit of a hack since we can't easily clear the file input value directly from here
                            // The parent component handles the state clearing
                            const input = document.getElementById(id) as HTMLInputElement;
                            if (input) input.value = '';
                            // Trigger change event with null/empty would be ideal but complex
                        }}
                    >
                        <span className="sr-only">Remove</span>
                    </Button>
                </div>
            )}
        </div>
    </div>
);

export default function FileUpload({ onGenerate }: FileUploadProps) {
    const [activeTab, setActiveTab] = useState("pdf");
    const [pitchDeck, setPitchDeck] = useState<File | null>(null);
    const [cmaFile, setCmaFile] = useState<File | null>(null);
    const [videoFile, setVideoFile] = useState<File | null>(null);
    const [audioFile, setAudioFile] = useState<File | null>(null);
    const [textInput, setTextInput] = useState('');
    const [processingMode, setProcessingMode] = useState<'fast' | 'research'>('research');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const { toast } = useToast();

    const handlePitchDeckChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setPitchDeck(event.target.files[0]);
        }
    };

    const handleCmaChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setCmaFile(event.target.files[0]);
        }
    };

    const handleVideoChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setVideoFile(event.target.files[0]);
            // Clear other inputs
            setPitchDeck(null);
            setAudioFile(null);
            setTextInput('');
        }
    };

    const handleAudioChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setAudioFile(event.target.files[0]);
            // Clear other inputs
            setPitchDeck(null);
            setVideoFile(null);
            setTextInput('');
        }
    };

    const handleTabChange = (value: string) => {
        setActiveTab(value);
        // Optional: Clear inputs when switching tabs? 
        // User requested "only one input at a time", so clearing might be safer to avoid confusion
        // User requested "only one input at a time", so clearing might be safer to avoid confusion
        // setPitchDeck(null);
        // setVideoFile(null);
        // setAudioFile(null);
        setTextInput('');
        setError(null);
    };

    const handleUploadClick = async () => {
        setError(null);

        // Validate based on active tab
        let hasInput = false;
        if (activeTab === 'pdf' && pitchDeck && cmaFile) hasInput = true;
        // if (activeTab === 'video' && videoFile) hasInput = true;
        // if (activeTab === 'audio' && audioFile) hasInput = true;
        // if (activeTab === 'text' && textInput.trim()) hasInput = true;

        if (!hasInput) {
            setError(`Please provide both a Pitch Deck and CMA Report.`);
            return;
        }

        setIsLoading(true);

        const formData = new FormData();

        // Append correct input based on active tab
        // Append files
        if (activeTab === 'pdf') {
            if (pitchDeck) formData.append('file', pitchDeck);
            if (cmaFile) formData.append('cma_report', cmaFile);
        }

        try {
            const response = await authenticatedFetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/upload?processing_mode=${processingMode}`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'An unknown error occurred' }));
                throw new Error(errorData.detail || 'File upload failed');
            }

            const result = await response.json();

            console.log('Upload successful:', result);
            toast({
                title: "Analysis Started",
                description: "Your data has been uploaded and analysis is underway.",
            });

            onGenerate();

        } catch (err: any) {
            const errorMessage = err.message || 'An unexpected error occurred during upload.';
            setError(errorMessage);
            toast({
                variant: "destructive",
                title: "Upload Failed",
                description: errorMessage,
            });
        } finally {
            setIsLoading(false);
        }
    };


    return (
        <div className="space-y-6">
            <div className="text-center">
                <div className="mx-auto bg-secondary p-3 rounded-full mb-4 inline-flex">
                    <UploadCloud className="w-8 h-8 text-primary" />
                </div>
                <h2 className="font-headline text-2xl font-bold">Create New Analysis</h2>
                <p className="text-sm text-muted-foreground mt-2">
                    Upload a pitch deck (PDF) and CMA Report (PDF/Excel) to generate a comprehensive startup analysis.
                </p>
            </div>

            <div className="space-y-6">


                {/* Input Type Tabs - REMOVED, strictly PDF + CMA */}
                <Tabs defaultValue="pdf" value={activeTab} onValueChange={handleTabChange} className="w-full">
                    <TabsList className="grid w-full grid-cols-1 mb-4">
                        <TabsTrigger value="pdf" className="flex items-center gap-2">
                            <FileText className="w-4 h-4" /> Required Files
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="pdf" className="mt-0 space-y-4">
                        <FileInput
                            id="pitch-deck-upload"
                            label="1. Upload Pitch Deck (PDF)"
                            icon={<FileText className="w-8 h-8 text-primary" />}
                            file={pitchDeck}
                            onFileChange={handlePitchDeckChange}
                            accept=".pdf"
                        />

                        <FileInput
                            id="cma-report-upload"
                            label="2. Upload CMA Report (PDF or Excel)"
                            icon={<FileText className="w-8 h-8 text-blue-500" />}
                            file={cmaFile}
                            onFileChange={handleCmaChange}
                            accept=".pdf,.xlsx,.xls"
                        />
                    </TabsContent>

                    {/* <TabsContent value="text" className="mt-0">
                        <div className="space-y-2">
                             <Label htmlFor="text-input" className="sr-only">Pitch Text</Label>
                             <Textarea
                                id="text-input"
                                value={textInput}
                                onChange={(e) => setTextInput(e.target.value)}
                                placeholder="Paste your pitch text, transcript, or startup description here..."
                                className="min-h-[200px] font-mono text-sm p-4"
                            />
                        </div>
                    </TabsContent> */}
                </Tabs>

                {error && (
                    <Alert variant="destructive">
                        <AlertTitle>Error</AlertTitle>
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                <Button size="lg" className="w-full font-bold h-12 text-lg" onClick={handleUploadClick} disabled={isLoading}>
                    {isLoading ? (
                        <>
                            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                            Analyzing Data...
                        </>
                    ) : (
                        'Start Analysis'
                    )}
                </Button>
            </div>
        </div >
    );
}
