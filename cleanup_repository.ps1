# 🧹 Script Pulizia Trading Bot Repository
# PowerShell script per automatizzare la pulizia

Write-Host "🧹 Inizio pulizia repository Trading Bot..." -ForegroundColor Green

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

$duplicateAiFiles = @(
    "ai_enhanced_analysis.py",
    "ai_trading_assistant.py",
    "ai_trading_chat.py", 
    "gemini_trading_assistant.py"
)

$documentationFiles = @(
    "frontend\CRASH_RECOVERY_README.md",
    "frontend\RECOVERY_IMPROVEMENTS_SUMMARY.md"
)

# Funzione per rimuovere file se esistono
function Remove-FileIfExists {
    param([string]$filePath)
    
    if (Test-Path $filePath) {
        Remove-Item $filePath -Force
        Write-Host "✅ Rimosso: $filePath" -ForegroundColor Yellow
        return $true
    } else {
        Write-Host "⚠️  Non trovato: $filePath" -ForegroundColor Gray
        return $false
    }
}

# Funzione per rimuovere cartella se esiste
function Remove-FolderIfExists {
    param([string]$folderPath)
    
    if (Test-Path $folderPath) {
        Remove-Item $folderPath -Recurse -Force
        Write-Host "✅ Rimossa cartella: $folderPath" -ForegroundColor Yellow
        return $true
    } else {
        Write-Host "⚠️  Cartella non trovata: $folderPath" -ForegroundColor Gray
        return $false
    }
}

# Contatori
$removedFiles = 0
$totalFiles = 0

Write-Host "`n🗑️  Rimozione file di test..." -ForegroundColor Cyan

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

Write-Host "`n🐛 Rimozione file debug..." -ForegroundColor Cyan

# Rimuovi file debug
foreach ($file in $debugFiles) {
    $totalFiles++
    if (Remove-FileIfExists $file) { $removedFiles++ }
}

Write-Host "`n📜 Rimozione file legacy..." -ForegroundColor Cyan

# Rimuovi file legacy
foreach ($file in $legacyFiles) {
    $totalFiles++
    if (Remove-FileIfExists $file) { $removedFiles++ }
}

Write-Host "`n🤖 Spostamento file AI in frontend/ai_modules..." -ForegroundColor Cyan

# Crea cartella ai_modules se non esiste
$aiModulesPath = "frontend\ai_modules"
if (-not (Test-Path $aiModulesPath)) {
    New-Item -ItemType Directory -Path $aiModulesPath -Force
    Write-Host "✅ Creata cartella: $aiModulesPath" -ForegroundColor Green
}

# Sposta file AI duplicati nella cartella ai_modules  
foreach ($file in $duplicateAiFiles) {
    $totalFiles++
    if (Test-Path $file) {
        $fileName = Split-Path $file -Leaf
        $destination = Join-Path $aiModulesPath $fileName
        
        # Se il file esiste già in ai_modules, rimuovi il duplicato
        if (Test-Path $destination) {
            Remove-Item $file -Force
            Write-Host "✅ Rimosso duplicato: $file (esiste già in ai_modules)" -ForegroundColor Yellow
            $removedFiles++
        } else {
            Move-Item $file $destination -Force
            Write-Host "✅ Spostato: $file -> $destination" -ForegroundColor Green
            $removedFiles++
        }
    }
}

Write-Host "`n📚 Rimozione documentazione duplicata..." -ForegroundColor Cyan

# Rimuovi documentazione duplicata
foreach ($file in $documentationFiles) {
    $totalFiles++
    if (Remove-FileIfExists $file) { $removedFiles++ }
}

Write-Host "`n🗂️  Pulizia cartelle..." -ForegroundColor Cyan

# Rimuovi cartelle legacy/inutili
$foldersToRemove = @(
    "Telgrambot_Multiallert",
    "__pycache__",
    "screenshots"  # Manteniamo solo se necessarie
)

foreach ($folder in $foldersToRemove) {
    if (Remove-FolderIfExists $folder) { $removedFiles++ }
}

# Pulizia cache Python ricorsiva
Get-ChildItem -Path . -Name "__pycache__" -Recurse -Directory | ForEach-Object {
    $fullPath = $_.FullName
    Remove-FolderIfExists $fullPath
}

Write-Host "`n🏗️  Creazione nuova struttura..." -ForegroundColor Cyan

# Crea cartelle per nuova struttura
$newFolders = @(
    "core",
    "docs", 
    "docker"
)

foreach ($folder in $newFolders) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force
        Write-Host "✅ Creata cartella: $folder" -ForegroundColor Green
    }
}

Write-Host "`n📊 Riassunto pulizia:" -ForegroundColor Green
Write-Host "   📁 File processati: $totalFiles" -ForegroundColor White
Write-Host "   🗑️  File rimossi: $removedFiles" -ForegroundColor White
Write-Host "   💾 Spazio liberato: ~$([math]::Round($removedFiles * 0.05, 2)) MB" -ForegroundColor White

Write-Host "`n✅ Pulizia completata!" -ForegroundColor Green
Write-Host "   🔍 Verifica che l'app funzioni: python frontend\app.py" -ForegroundColor Yellow
Write-Host "   📝 Log completo salvato in CLEANUP_LOG.txt" -ForegroundColor Gray

# Salva log in file
$logContent = @"
Pulizia Repository Trading Bot - $(Get-Date)
======================================

File processati: $totalFiles  
File rimossi: $removedFiles
Spazio liberato stimato: ~$([math]::Round($removedFiles * 0.05, 2)) MB

Prossimi step:
1. Testare avvio applicazione: python frontend\app.py
2. Verificare funzionalità principali
3. Continuare con ristrutturazione core
"@

$logContent | Out-File -FilePath "CLEANUP_LOG.txt" -Encoding UTF8

Write-Host "`nℹ️  Prossimi step nella roadmap:" -ForegroundColor Blue
Write-Host "   1. Testare l'applicazione" -ForegroundColor White  
Write-Host "   2. Ristrutturare core files" -ForegroundColor White
Write-Host "   3. Preparare architettura multi-tenant" -ForegroundColor White