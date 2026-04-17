# gitc.ps1 — GroupsGuru Git Shortcut
# Usage: .\gitc.ps1 "Your commit message"

$msg = $args[0]
if (-not $msg) { $msg = "Automated sync via Git C" }

Write-Host "🚀 Starting Git C (Add, Commit, Push)..." -ForegroundColor Cyan

git add .
git commit -m $msg
git push origin master

Write-Host "✅ Git C Complete. Changes are live." -ForegroundColor Green
