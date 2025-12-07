# PITCHLENS BACKEND DEPLOYMENT SCRIPT
# Service: pitchlens-backend
# This script deploys the backend API to Google Cloud Run

$SERVICE_NAME = "pitchlens-backend"
$REGION = "us-central1"
$PROJECT_ID = "hackathon-472304"

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "       DEPLOYING PITCHLENS BACKEND TO CLOUD RUN           " -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify in project folder
Write-Host "Step 1: Verifying project..." -ForegroundColor Yellow
if (-Not (Test-Path "main.py")) {
    Write-Host "[ERROR] main.py not found! Are you in the Backend folder?" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Found main.py" -ForegroundColor Green
Write-Host ""

# Step 2: Set project
Write-Host "Step 2: Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID --quiet
gcloud config set compute/region $REGION --quiet
Write-Host "[OK] Project: $PROJECT_ID" -ForegroundColor Green
Write-Host "[OK] Region: $REGION" -ForegroundColor Green
Write-Host ""

# Step 3: Deploy
Write-Host "Step 3: Deploying backend (2-3 minutes)..." -ForegroundColor Yellow
Write-Host "Please wait..." -ForegroundColor Gray
Write-Host ""

# IMPORTANT: Update FRONTEND_URL after deploying the frontend!
$FRONTEND_URL = "https://pitchlens-frontend-wehui2z6iq-uc.a.run.app"

# Load .env file if it exists
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, [System.EnvironmentVariableTarget]::Process)
        }
    }
    Write-Host "Loaded environment variables from .env" -ForegroundColor Green
} else {
    Write-Warning ".env file not found. Ensure environment variables are set."
}

# Check for required environment variables
if (-not $env:BREVO_API_KEY) { Write-Warning "BREVO_API_KEY not set. Deployment may fail." }
if (-not $env:GEMINI_API_KEY) { Write-Warning "GEMINI_API_KEY not set. Deployment may fail." }

gcloud run deploy $SERVICE_NAME `
  --source . `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --memory 2Gi `
  --cpu 1 `
  --timeout 3600 `
  --max-instances 10 `
  --set-env-vars="GCP_PROJECT_ID=hackathon-472304,GCP_LOCATION=us-central1,DOCUMENT_AI_PROCESSOR_ID=83d8d6c1534977bb,DOCUMENT_AI_LOCATION=us,GCS_BUCKET_NAME=investment_memo_ai,BREVO_API_KEY=$env:BREVO_API_KEY,FROM_EMAIL=$env:FROM_EMAIL,GEMINI_API_KEY=$env:GEMINI_API_KEY,FRONTEND_URL=$FRONTEND_URL" `
  --quiet

# Check result
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] Backend deployment successful!" -ForegroundColor Green
    Write-Host ""
    
    # Get URL
    Write-Host "Step 4: Getting service URL..." -ForegroundColor Yellow
    $BACKEND_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'
    
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Green
    Write-Host "              BACKEND DEPLOYMENT COMPLETE!                " -ForegroundColor Green
    Write-Host "=============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Backend API URL:" -ForegroundColor Cyan
    Write-Host "   $BACKEND_URL" -ForegroundColor Green
    Write-Host ""
    Write-Host "API Documentation:" -ForegroundColor Cyan
    Write-Host "   $BACKEND_URL/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "IMPORTANT NEXT STEPS:" -ForegroundColor Yellow
    Write-Host "   1. Copy the backend URL above" -ForegroundColor White
    Write-Host "   2. Update Frontend/.env.production with:" -ForegroundColor White
    Write-Host "      NEXT_PUBLIC_API_BASE_URL=$BACKEND_URL" -ForegroundColor Gray
    Write-Host "   3. Deploy frontend using: .\deploy-frontend.ps1" -ForegroundColor White
    Write-Host "   4. After frontend deployment, update this script's FRONTEND_URL and re-deploy" -ForegroundColor White
    Write-Host ""
    Write-Host "View logs:" -ForegroundColor Cyan
    Write-Host "   gcloud run logs read $SERVICE_NAME --region $REGION --follow" -ForegroundColor Gray
    Write-Host ""
    
    # Save URL to file for easy reference
    $BACKEND_URL | Out-File -FilePath "backend-url.txt" -Encoding UTF8
    Write-Host "[SAVED] Backend URL saved to: backend-url.txt" -ForegroundColor Green
    Write-Host ""
    
} else {
    Write-Host ""
    Write-Host "[ERROR] Deployment failed!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Red
    exit 1
}
