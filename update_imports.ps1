# Script PowerShell per aggiornare tutti gli import paths
# Aggiorna i percorsi da config -> core.config e trading_functions -> core.trading_functions

Write-Host "🔄 Aggiornamento import paths per architettura core..." -ForegroundColor Green

# Lista dei file da processare
$filesToUpdate = @(
    "frontend\utils\trading_wrapper.py",
    "frontend\utils\bot_functions.py", 
    "frontend\utils\advanced_exit_strategies.py",
    "frontend\utils\telegram_bot.py",
    "frontend\utils\crash_recovery.py",
    "frontend\start_telegram_bot.py",
    "frontend\routes\websocket.py",
    "frontend\routes\trading.py",
    "frontend\routes\symbols.py",
    "frontend\routes\history.py",
    "frontend\routes\bot_control.py",
    "strategies\triple_confirmation.py",
    "strategies\ema_strategy.py"
)

$updatedFiles = 0

foreach ($file in $filesToUpdate) {
    if (Test-Path $file) {
        Write-Host "📝 Aggiornando: $file" -ForegroundColor Yellow
        
        # Leggi il contenuto del file
        $content = Get-Content $file -Raw -Encoding UTF8
        
        # Flag per tracciare se ci sono stati cambiamenti
        $changed = $false
        
        # Sostituzioni per config
        if ($content -match "from config import") {
            $content = $content -replace "from config import", "from core.config import"
            $changed = $true
        }
        
        if ($content -match "import config") {
            $content = $content -replace "import config", "import core.config as config"  
            $changed = $true
        }
        
        # Sostituzioni per trading_functions
        if ($content -match "from trading_functions import") {
            $content = $content -replace "from trading_functions import", "from core.trading_functions import"
            $changed = $true
        }
        
        if ($content -match "import trading_functions") {
            $content = $content -replace "import trading_functions", "import core.trading_functions as trading_functions"
            $changed = $true
        }
        
        # Salva solo se ci sono stati cambiamenti
        if ($changed) {
            $content | Set-Content $file -Encoding UTF8
            Write-Host "✅ Aggiornato: $file" -ForegroundColor Green
            $updatedFiles++
        } else {
            Write-Host "ℹ️  Nessun cambiamento necessario: $file" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️  File non trovato: $file" -ForegroundColor Red
    }
}

Write-Host "`n📊 Aggiornamento completato!" -ForegroundColor Green
Write-Host "   📁 File processati: $($filesToUpdate.Count)" -ForegroundColor White
Write-Host "   ✅ File aggiornati: $updatedFiles" -ForegroundColor White

Write-Host "`n🧪 Test degli import..." -ForegroundColor Cyan
Set-Location frontend
python -c "import sys; sys.path.append('..'); from core.config import api; from core.trading_functions import mostra_saldo; print('✅ Import core modules successful')"
Set-Location ..