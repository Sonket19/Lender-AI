'use client';

import FileUpload from '@/components/file-upload';
import Header from '@/components/header';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth-provider';
import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export default function UploadPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/');
    }
  }, [user, authLoading, router]);

  const handleGenerate = () => {
    // This would ideally be a real navigation after a real analysis is created.
    // For now, it just navigates to the first mock startup.
    router.push('/startup/sia');
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
      <main className="flex-1 container mx-auto px-4 py-8 md:py-12 flex items-center justify-center">
        <div className="w-full">
          <FileUpload onGenerate={handleGenerate} />
        </div>
      </main>
    </div>
  );
}
