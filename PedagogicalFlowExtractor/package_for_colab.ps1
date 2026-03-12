# Package PedagogicalFlowExtractor for Google Colab deployment
# This creates a compressed archive of all necessary files

Write-Host "📦 Packaging PedagogicalFlowExtractor for Google Colab..." -ForegroundColor Cyan
Write-Host ""

# Navigate to script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Remove old archive if it exists
if (Test-Path "PedagogicalFlowExtractor_Colab.zip") {
    Remove-Item "PedagogicalFlowExtractor_Colab.zip" -Force
}

Write-Host "Creating ZIP archive..." -ForegroundColor Yellow

# Create list of files to include
$filesToInclude = @()

# Add directories
$directories = @("pipeline", "utils", "visualization", "app")
foreach ($dir in $directories) {
    if (Test-Path $dir) {
        Get-ChildItem -Path $dir -Recurse -File | Where-Object {
            $_.Extension -ne ".pyc" -and
            $_.Directory.Name -ne "__pycache__"
        } | ForEach-Object {
            $filesToInclude += $_.FullName
        }
    }
}

# Add data JSON files
if (Test-Path "data") {
    Get-ChildItem -Path "data\*.json" | ForEach-Object {
        $filesToInclude += $_.FullName
    }
}

# Add config files
$configFiles = @("config.yaml", "requirements.txt", "README.md")
foreach ($file in $configFiles) {
    if (Test-Path $file) {
        $filesToInclude += (Get-Item $file).FullName
    }
}

# Create ZIP using .NET
Add-Type -Assembly System.IO.Compression.FileSystem
$zipPath = Join-Path $scriptPath "PedagogicalFlowExtractor_Colab.zip"
$zip = [System.IO.Compression.ZipFile]::Open($zipPath, 'Create')

$baseDir = $scriptPath
foreach ($file in $filesToInclude) {
    $relativePath = $file.Substring($baseDir.Length + 1)
    $entry = $zip.CreateEntry($relativePath)
    $entryStream = $entry.Open()
    $fileStream = [System.IO.File]::OpenRead($file)
    $fileStream.CopyTo($entryStream)
    $fileStream.Close()
    $entryStream.Close()
}

$zip.Dispose()

# Get file size
$size = (Get-Item $zipPath).Length / 1MB
$sizeStr = "{0:N2} MB" -f $size

Write-Host ""
Write-Host "✅ Package created: PedagogicalFlowExtractor_Colab.zip ($sizeStr)" -ForegroundColor Green
Write-Host ""
Write-Host "📤 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open PedagogicalKG_Complete_Colab.ipynb in Google Colab"
Write-Host "  2. Upload PedagogicalFlowExtractor_Colab.zip when prompted"
Write-Host "  3. The notebook will extract and run Streamlit automatically"
Write-Host "  4. Access your app via the public ngrok URL"
Write-Host ""
Write-Host "🌐 Or upload to Google Drive first for easier repeated access" -ForegroundColor Yellow
Write-Host ""
