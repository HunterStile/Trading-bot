# Setup Docker per Trading Bot Dashboards - PowerShell Version
# Questo script configura e avvia tutti i servizi dashboard in Docker su Windows

param(
    [switch]$CleanImages = $false
)

Write-Host "🚀 Setting up Trading Bot Dashboards with Docker..." -ForegroundColor Blue

# Funzioni per colori
function Write-Status($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Write-Success($message) {
    Write-Host "[SUCCESS] $message" -ForegroundColor Green
}

function Write-Warning($message) {
    Write-Host "[WARNING] $message" -ForegroundColor Yellow
}

function Write-Error($message) {
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

# Controllo Docker
try {
    docker --version | Out-Null
    Write-Status "Docker trovato"
} catch {
    Write-Error "Docker non è installato o non è in PATH"
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Status "Docker Compose trovato"
} catch {
    Write-Error "Docker Compose non è installato"
    exit 1
}

# Vai nella directory corretta
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptDir "..")
Write-Status "Working directory: $(Get-Location)"

# Crea directory necessarie
Write-Status "Creando directory necessarie..."
$directories = @("data", "logs", "backups", "docker\ssl")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Status "Creata directory: $dir"
    }
}

# Verifica file dashboard
Write-Status "Verificando file dashboard..."
$dashboardFiles = @("simple_dashboard.py", "professional_dashboard.py", "multi_symbol_dashboard.py", "fixed_dashboard.py")
foreach ($file in $dashboardFiles) {
    if (!(Test-Path $file)) {
        Write-Warning "$file non trovato nella root directory"
    } else {
        Write-Status "$file ✓"
    }
}

# Crea .env se non esiste
if (!(Test-Path ".env")) {
    Write-Status "Creando file .env..."
    $envContent = @"
# Trading Bot Dashboards Environment Variables
FLASK_ENV=production
PYTHONPATH=/app
PYTHONUNBUFFERED=1
REDIS_PASSWORD=dashboards2024

# Optional: API Keys (se necessario per future integrazioni)
# BYBIT_API_KEY=your_api_key
# BYBIT_SECRET=your_secret
# TELEGRAM_BOT_TOKEN=your_bot_token
"@
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success "File .env creato"
} else {
    Write-Status "File .env già esistente"
}

# Vai in directory docker
Set-Location "docker"

# Ferma container esistenti
Write-Status "Fermando container esistenti..."
try {
    docker-compose -f docker-compose.dashboards.yml down 2>$null
} catch {
    Write-Status "Nessun container da fermare"
}

# Pulisci immagini se richiesto
if ($CleanImages) {
    Write-Status "Rimuovendo immagini vecchie..."
    docker system prune -f
}

# Build immagini
Write-Status "Building immagini Docker..."
try {
    docker-compose -f docker-compose.dashboards.yml build --no-cache
    Write-Success "Build completato"
} catch {
    Write-Error "Errore durante build"
    exit 1
}

# Avvia servizi
Write-Status "Avviando servizi dashboard..."
try {
    docker-compose -f docker-compose.dashboards.yml up -d
    Write-Success "Servizi avviati"
} catch {
    Write-Error "Errore durante avvio"
    exit 1
}

# Attendi avvio
Write-Status "Attendendo avvio servizi..."
Start-Sleep -Seconds 15

# Controllo health
Write-Status "Controllando health dei servizi..."
$services = @(
    @{Name="dashboard-multi-simple"; Port=5007},
    @{Name="dashboard-professional"; Port=5006},
    @{Name="dashboard-simple"; Port=5004},
    @{Name="dashboard-fixed"; Port=5003}
)

foreach ($service in $services) {
    try {
        $containers = docker ps --format "table {{.Names}}" | Select-String $service.Name
        if ($containers) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/debug" -TimeoutSec 5 -UseBasicParsing
                Write-Success "$($service.Name) è online (porta $($service.Port))"
            } catch {
                try {
                    $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/" -TimeoutSec 5 -UseBasicParsing
                    Write-Success "$($service.Name) è online (porta $($service.Port))"
                } catch {
                    Write-Warning "$($service.Name) è running ma non risponde su porta $($service.Port)"
                }
            }
        } else {
            Write-Error "$($service.Name) non è in running"
        }
    } catch {
        Write-Warning "Errore nel controllo di $($service.Name)"
    }
}

# Status finale
Write-Success "Setup Docker completato!"
Write-Host ""
Write-Host "🌐 Servizi disponibili:" -ForegroundColor Yellow
Write-Host "  • Multi-Symbol Dashboard:  http://localhost/ (porta 80, proxy)" -ForegroundColor White
Write-Host "  • Dashboard Professionale: http://localhost/professional" -ForegroundColor White
Write-Host "  • Dashboard Semplice:      http://localhost/simple" -ForegroundColor White
Write-Host "  • Dashboard Fixed:         http://localhost/fixed" -ForegroundColor White
Write-Host ""
Write-Host "🔗 Accesso diretto:" -ForegroundColor Yellow
Write-Host "  • Multi-Symbol: http://localhost:5007" -ForegroundColor White
Write-Host "  • Professionale: http://localhost:5006" -ForegroundColor White
Write-Host "  • Semplice: http://localhost:5004" -ForegroundColor White
Write-Host "  • Fixed: http://localhost:5003" -ForegroundColor White
Write-Host ""
Write-Host "🛠️ Monitoring:" -ForegroundColor Yellow
Write-Host "  • Portainer: http://localhost:9000 (admin/admin123)" -ForegroundColor White
Write-Host "  • Redis: localhost:6379 (password: dashboards2024)" -ForegroundColor White
Write-Host ""
Write-Host "📊 Comandi utili:" -ForegroundColor Yellow
Write-Host "  • docker-compose -f docker-compose.dashboards.yml logs -f" -ForegroundColor Gray
Write-Host "  • docker-compose -f docker-compose.dashboards.yml restart" -ForegroundColor Gray
Write-Host "  • docker-compose -f docker-compose.dashboards.yml down" -ForegroundColor Gray
Write-Host ""
Write-Success "Enjoy your trading dashboards! 🚀📈"