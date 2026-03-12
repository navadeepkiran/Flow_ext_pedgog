# Setup and push Pedagogical Flow Extractor to GitHub
# PowerShell script for Windows

Write-Host "🚀 Setting up GitHub repository for Pedagogical Flow Extractor" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "📁 Initializing git repository..." -ForegroundColor Yellow
    git init
} else {
    Write-Host "✅ Git repository already exists" -ForegroundColor Green
}

# Check if API key is secured
if (Test-Path ".env") {
    Write-Host "🔒 .env file found - checking for API keys..." -ForegroundColor Yellow
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "gsk_") {
        Write-Host "⚠️  WARNING: .env contains API keys!" -ForegroundColor Red
        Write-Host "   Make sure .env is in .gitignore" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  No .env file found. Create one from .env.example" -ForegroundColor Yellow
}

# Add all files (gitignore will exclude sensitive ones)
Write-Host "📦 Adding files to git..." -ForegroundColor Yellow
git add .

# Check what's being committed
Write-Host ""
Write-Host "📋 Files to be committed:" -ForegroundColor Cyan
git diff --cached --name-only

# Check if sensitive files are accidentally staged
Write-Host ""
Write-Host "🔍 Checking for sensitive data..." -ForegroundColor Yellow
$stagedFiles = git diff --cached --name-only
$sensitiveFiles = $stagedFiles | Where-Object { $_ -match "(\.env$|api_key|secret)" }

if ($sensitiveFiles) {
    Write-Host "❌ DANGER: Sensitive files detected in staging area!" -ForegroundColor Red
    Write-Host "   These files should be in .gitignore:" -ForegroundColor Yellow
    $sensitiveFiles | ForEach-Object { Write-Host "   $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "   Run: git reset HEAD <file> to unstage" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "✅ No sensitive files detected" -ForegroundColor Green
}

# Commit changes
Write-Host ""
Write-Host "💾 Committing changes..." -ForegroundColor Yellow
$commitMessage = @"
Initial commit: Pedagogical Knowledge Graph Extractor

- Complete pipeline: STT, normalization, extraction, graph building
- Multi-language support: English, Hinglish, Tenglish  
- LLM and rule-based extraction modes
- Interactive Streamlit web interface
- Google Colab integration with ngrok tunneling
- Environment-based configuration (.env support)
- Telugu script transliteration
- Community detection and PageRank analysis
- Export options: JSON, HTML, reports
"@

git commit -m $commitMessage

# Check if remote exists
$remoteUrl = $null
try {
    $remoteUrl = git remote get-url origin 2>$null
    Write-Host "✅ Remote 'origin' already configured" -ForegroundColor Green
    Write-Host "   Remote URL: $remoteUrl" -ForegroundColor Cyan
} catch {
    Write-Host "🔗 Setting up remote repository..." -ForegroundColor Yellow
    Write-Host "   Please set your GitHub repository URL:" -ForegroundColor Cyan
    Write-Host "   Example: https://github.com/navadeepkiran/Pedagogical_flow_extractor.git" -ForegroundColor Gray
    Write-Host ""
    
    $repoUrl = Read-Host "Enter repository URL"
    
    if ([string]::IsNullOrWhiteSpace($repoUrl)) {
        Write-Host "❌ No URL provided. Please run:" -ForegroundColor Red
        Write-Host "   git remote add origin https://github.com/USERNAME/REPO.git" -ForegroundColor Yellow
        exit 1
    }
    
    git remote add origin $repoUrl
    Write-Host "✅ Remote added: $repoUrl" -ForegroundColor Green
    $remoteUrl = $repoUrl
}

# Push to GitHub
Write-Host ""
Write-Host "🚀 Pushing to GitHub..." -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🎉 SUCCESS! Repository pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Visit your GitHub repository" -ForegroundColor White
    Write-Host "   2. Update README.md with your repository URL" -ForegroundColor White
    Write-Host "   3. Test Colab notebook with your new GitHub link" -ForegroundColor White
    Write-Host "   4. Share your project!" -ForegroundColor White
    Write-Host ""
    Write-Host "🔗 Colab link format:" -ForegroundColor Cyan
    
    # Extract username and repo from URL
    if ($remoteUrl -match "github\.com[:/]([^/]+)/([^/.]+)") {
        $username = $matches[1]
        $reponame = $matches[2]
        $colabUrl = "https://colab.research.google.com/github/$username/$reponame/blob/main/PedagogicalKG_GitHub_Colab.ipynb"
        Write-Host "   $colabUrl" -ForegroundColor Yellow
    } else {
        Write-Host "   https://colab.research.google.com/github/USERNAME/Pedagogical_flow_extractor/blob/main/PedagogicalKG_GitHub_Colab.ipynb" -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Push failed. Common issues:" -ForegroundColor Red
    Write-Host "   - Repository doesn't exist on GitHub" -ForegroundColor Yellow
    Write-Host "   - Authentication required (setup SSH keys or token)" -ForegroundColor Yellow
    Write-Host "   - Branch protection rules" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 Try:" -ForegroundColor Cyan
    Write-Host "   git push --set-upstream origin main" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")