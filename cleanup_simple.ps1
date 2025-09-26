# Script Pulizia Trading Bot Repository
# PowerShell script per automatizzare la pulizia

Write-Host "Inizio pulizia repository Trading Bot..." -ForegroundColor Green

# Lista file da rimuovere
$testFiles = @(
    "test_visualization.py",
    "test_timeframes.py", 
    "test_telegram_config.py",
    "test_quick.py",
    "test_docker.py",
    "test_daily_fix.py",
    "test_backtest_system.py",
    "test_api.py",
    "test_all_timeframes.py",
    "test_advanced_exit_strategies.py"
)

$frontendTestFiles = @(
    "frontend\test_anti_duplicates.py",
    "frontend\test_recovery_bybit.py", 
    "frontend\test_complete_workflow.py",
    "frontend\test_telegram_integration.py",
    "frontend\test_recovery_improvements.py",
    "frontend\test_recovery_close.py"
)

$debugFiles = @(
    "frontend\debug_history.html",
    "frontend\ultra_simple_history.html",
    "frontend\get_chat_id.py",
    "get_group_chat_id.py",
    "acquisire_id.py"
)

$legacyFiles = @(
    "Telegrambot_allert.py",
    "chiusura operazioni.py",
    "Apertura e chiusura operazioni.py",
    "simple_backtest.py",
    "backtest.py"
)

# Funzione per rimuovere file se esistono
function Remove-FileIfExists {
    param([string]$filePath)
    
    if (Test-Path $filePath) {
        Remove-Item $filePath -Force
        Write-Host "Rimosso: $filePath" -ForegroundColor Yellow
        return $true
    } else {
        Write-Host "Non trovato: $filePath" -ForegroundColor Gray
        return $false
    }
}

# Contatori
$removedFiles = 0
$totalFiles = 0

Write-Host "Rimozione file di test..." -ForegroundColor Cyan

# Rimuovi file di test root
foreach ($file in $testFiles) {
    $totalFiles++
    if (Remove-FileIfExists $file) { $removedFiles++ }
}

# Rimuovi file di test frontend  
foreach ($file in $frontendTestFiles) {
    $totalFiles++
    if (Remove-FileIfExists $file) { $removedFiles++ }
}

Write-Host "Rimozione file debug..." -ForegroundColor Cyan

# Rimuovi file debug
foreach ($file in $debugFiles) {
    $totalFiles++
    if (Remove-FileIfExists $file) { $removedFiles++ }
}

Write-Host "Rimozione file legacy..." -ForegroundColor Cyan

# Rimuovi file legacy
foreach ($file in $legacyFiles) {
    $totalFiles++
    if (Remove-FileIfExists $file) { $removedFiles++ }
}

Write-Host "Rimozione cartelle inutili..." -ForegroundColor Cyan

# Rimuovi cartelle
if (Test-Path "Telgrambot_Multiallert") {
    Remove-Item "Telgrambot_Multiallert" -Recurse -Force
    Write-Host "Rimossa cartella: Telgrambot_Multiallert" -ForegroundColor Yellow
    $removedFiles++
}

# Pulizia cache Python
Get-ChildItem -Path . -Name "__pycache__" -Recurse -Directory | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    Write-Host "Rimossa cache: $($_.FullName)" -ForegroundColor Yellow
}

Write-Host "Riassunto pulizia:" -ForegroundColor Green
Write-Host "File processati: $totalFiles" -ForegroundColor White
Write-Host "File rimossi: $removedFiles" -ForegroundColor White

Write-Host "Pulizia completata!" -ForegroundColor Green
Write-Host "Verifica che l'app funzioni: python frontend\app.py" -ForegroundColor Yellow