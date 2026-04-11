# Run demo using Apify if APIFY_TOKEN is present
# Usage: Open PowerShell in repo root and run: .\scripts\run_with_apify.ps1

# load .env if present
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path Env:$name -Value $value
        }
    }
}

if (-not $env:APIFY_TOKEN) {
    Write-Host "Warning: APIFY_TOKEN not set. The script will run using local scrapers unless you set APIFY_TOKEN." -ForegroundColor Yellow
}
else {
    Write-Host "APIFY_TOKEN found. Demo will prefer Apify actor runs (USE_LOCAL_SCRAPER auto)." -ForegroundColor Green
}

# Run demo
python run_demo.py

# Open reports folder if a report was generated
if (Test-Path reports) {
    Write-Host "Reports directory:" (Get-ChildItem reports | Sort-Object LastWriteTime -Descending | Select-Object -First 5).Name
}
