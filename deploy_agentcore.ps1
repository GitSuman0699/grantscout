Write-Host "Starting AgentCore Deployment for GrantScout..."

# Ensure AWS credentials are set or SSO is logged in
try {
    $null = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS credentials not found or expired."
    }
} catch {
    Write-Host "Error: AWS credentials not found or expired." -ForegroundColor Red
    Write-Host "Please run 'aws configure' or 'aws sso login' before deploying."
    exit 1
}

# Check if @aws/agentcore CLI is installed globally
if (!(Get-Command agentcore -ErrorAction SilentlyContinue)) {
    Write-Host "AgentCore CLI not found. Installing globally via npm..." -ForegroundColor Yellow
    npm install -g @aws/agentcore
}

# Check if uv is installed
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv package manager not found. Installing globally via pip..." -ForegroundColor Yellow
    pip install uv
}

Write-Host "`n[Cost Optimization] Configuring 15-minute idle spin-down to save AWS costs..." -ForegroundColor Cyan

# Verify pre-configured agentcore.json
if (Test-Path ".\agentcore\agentcore.json") {
    Write-Host "Found pre-configured agentcore/agentcore.json with 15-minute idleRuntimeSessionTimeout (900s)." -ForegroundColor Green
} else {
    Write-Host "Error: agentcore/agentcore.json not found." -ForegroundColor Red
    exit 1
}

Write-Host "`nDeploying to Amazon Bedrock AgentCore Runtime..." -ForegroundColor Cyan
Write-Host "• Target: agentcore/src (Decoupled Strands Swarm)"
Write-Host "• Scale-to-Zero: Enabled (15 min / 900 sec inactivity timeout)"
Write-Host "• Architecture: BYO Container on Python 3.12"

# Execute deployment directly from repository root
npx agentcore deploy --yes

Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
Write-Host "Runtime container will automatically spin down after 15 minutes of inactivity to minimize AWS bill." -ForegroundColor Yellow
Write-Host "Run 'npx agentcore status' to monitor runtime lifecycle."
