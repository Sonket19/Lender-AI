
$Content = @"
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyBLXGvGR7uf50WKlvC2POV-ACrzqhtJTbQ
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=lenderai-new-8d2a.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=lenderai-new-8d2a
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=lenderai-new-8d2a.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id_here
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id_here
NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID=your_measurement_id_here
"@

Set-Content -Path "f:\Icic\Frontend\.env.local" -Value $Content -Force
Write-Host "Restored .env.local with partial Firebase keys"
