$ROOT    = "D:\projet\Audit_Comptable\probare"
$ENGINE  = "$ROOT\apps\engine"
$DESKTOP = "$ROOT\apps\desktop"
$PORT    = 8767

Write-Host ""
Write-Host "  === PROBARE - Demarrage ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verifier les prerequis
Write-Host "  > Verification des prerequis..." -ForegroundColor Gray

$pyVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERREUR] Python introuvable." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] $pyVersion" -ForegroundColor Green

$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERREUR] Node.js introuvable." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Node $nodeVersion" -ForegroundColor Green

# 2. Demarrer le backend Python
Write-Host ""
Write-Host "  > Demarrage du moteur Python (port $PORT)..." -ForegroundColor Cyan

$env:PYTHONPATH = "D:\pip\packages"

$backendJob = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "probare_engine.main:app", "--host", "127.0.0.1", "--port", "$PORT", "--no-access-log" `
    -WorkingDirectory $ENGINE `
    -NoNewWindow `
    -PassThru

Write-Host "  > PID backend : $($backendJob.Id)" -ForegroundColor Gray

# 3. Attendre que le backend soit pret
Write-Host "  > En attente du backend" -NoNewline -ForegroundColor Cyan
$timeout = 30
$elapsed = 0
$ready   = $false

while ($elapsed -lt $timeout) {
    Start-Sleep -Milliseconds 500
    $elapsed += 0.5
    Write-Host "." -NoNewline -ForegroundColor Gray
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$PORT/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # pas encore pret
    }
}

Write-Host ""

if (-not $ready) {
    Write-Host "  [ERREUR] Backend non disponible apres ${timeout}s." -ForegroundColor Red
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "  [OK] Backend pret sur http://127.0.0.1:$PORT" -ForegroundColor Green

# 4. Lancer Electron
Write-Host ""
Write-Host "  > Demarrage de l'application Electron..." -ForegroundColor Cyan

$electronJob = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run dev" `
    -WorkingDirectory $DESKTOP `
    -NoNewWindow `
    -PassThru

if (-not $electronJob) {
    Write-Host "  [ERREUR] Impossible de lancer Electron." -ForegroundColor Red
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "  [OK] Electron lance (PID : $($electronJob.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "  Probare est en cours d'execution." -ForegroundColor Cyan
Write-Host "  Fermez la fenetre Electron pour arreter." -ForegroundColor Cyan
Write-Host "  Ctrl+C ici pour tout couper." -ForegroundColor Cyan
Write-Host ""

# 5. Attendre la fermeture d'Electron puis stopper le backend
$electronJob.WaitForExit()

Write-Host ""
Write-Host "  > Arret du backend Python..." -ForegroundColor Yellow
Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
Write-Host "  [OK] Arret propre." -ForegroundColor Green
