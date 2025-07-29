# Script PowerShell per gestire l'applicazione TradingView Clone

param(
    [Parameter(Position=0)]
    [string]$Command,
    
    [Parameter(Position=1)]
    [string]$Service
)

# Funzioni di utilità per output colorato
function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Funzione di help
function Show-Help {
    @"
🔧 TradingView Clone - Docker Management Script (PowerShell)

USAGE:
    .\docker-tools.ps1 [COMMAND] [OPTIONS]

COMMANDS:
    dev                 Avvia l'ambiente di sviluppo
    prod                Avvia l'ambiente di produzione
    build               Build delle immagini Docker
    clean               Pulisce containers e immagini
    logs                Mostra i logs dei servizi
    restart             Riavvia i servizi
    stop                Ferma tutti i servizi
    status              Mostra lo stato dei servizi
    shell-backend       Apre una shell nel container backend
    shell-frontend      Apre una shell nel container frontend
    backup-db           Crea un backup del database
    restore-db          Ripristina il database da backup

EXAMPLES:
    .\docker-tools.ps1 dev           # Avvia ambiente di sviluppo
    .\docker-tools.ps1 prod          # Avvia ambiente di produzione
    .\docker-tools.ps1 logs backend  # Mostra logs del backend
    .\docker-tools.ps1 clean         # Pulisce tutto
"@
}

# Funzione per sviluppo
function Start-Dev {
    Write-Info "Avvio ambiente di sviluppo..."
    docker-compose -f docker-compose.yml up -d
    Write-Success "Ambiente di sviluppo avviato!"
    Write-Info "Frontend: http://localhost:3000"
    Write-Info "Backend: http://localhost:5000"
    Write-Info "MongoDB: localhost:27017"
}

# Funzione per produzione
function Start-Prod {
    Write-Info "Avvio ambiente di produzione..."
    
    # Controlla se esiste .env
    if (-not (Test-Path ".env")) {
        Write-Warning "File .env non trovato. Copio .env.example..."
        Copy-Item ".env.example" ".env"
        Write-Warning "⚠️ IMPORTANTE: Modifica il file .env con i tuoi valori reali!"
        Read-Host "Premi Enter per continuare quando hai modificato .env"
    }
    
    docker-compose -f docker-compose.prod.yml up -d
    Write-Success "Ambiente di produzione avviato!"
    Write-Info "Applicazione: http://localhost"
    Write-Info "API: http://localhost:5000"
}

# Build delle immagini
function Build-Images {
    Write-Info "Build delle immagini Docker..."
    docker-compose -f docker-compose.yml build
    docker-compose -f docker-compose.prod.yml build
    Write-Success "Build completato!"
}

# Pulizia
function Clean-All {
    Write-Warning "Pulizia containers e immagini..."
    docker-compose -f docker-compose.yml down -v --rmi all
    docker-compose -f docker-compose.prod.yml down -v --rmi all
    docker system prune -f
    Write-Success "Pulizia completata!"
}

# Logs
function Show-Logs {
    param([string]$ServiceName)
    if ([string]::IsNullOrEmpty($ServiceName)) {
        docker-compose logs -f
    } else {
        docker-compose logs -f $ServiceName
    }
}

# Restart
function Restart-Services {
    Write-Info "Riavvio servizi..."
    docker-compose restart
    Write-Success "Servizi riavviati!"
}

# Stop
function Stop-Services {
    Write-Info "Arresto servizi..."
    docker-compose down
    docker-compose -f docker-compose.prod.yml down
    Write-Success "Servizi arrestati!"
}

# Status
function Show-Status {
    Write-Info "Stato dei servizi:"
    docker-compose ps
    Write-Host ""
    docker-compose -f docker-compose.prod.yml ps
}

# Shell backend
function Shell-Backend {
    Write-Info "Apertura shell nel container backend..."
    docker-compose exec backend sh
}

# Shell frontend
function Shell-Frontend {
    Write-Info "Apertura shell nel container frontend..."
    docker-compose exec frontend sh
}

# Backup database
function Backup-Database {
    $backupName = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Info "Creazione backup database: $backupName"
    
    # Crea directory backups se non esiste
    if (-not (Test-Path "backups")) {
        New-Item -ItemType Directory -Name "backups"
    }
    
    docker-compose exec mongo mongodump --db tradingview_clone --out /tmp/$backupName
    $mongoContainer = docker-compose ps -q mongo
    docker cp "${mongoContainer}:/tmp/$backupName" "./backups/"
    Write-Success "Backup creato: ./backups/$backupName"
}

# Restore database
function Restore-Database {
    param([string]$BackupDir)
    if ([string]::IsNullOrEmpty($BackupDir)) {
        Write-Error-Custom "Specifica la directory del backup"
        Write-Host "Uso: .\docker-tools.ps1 restore-db <backup_directory>"
        return
    }
    
    Write-Warning "Ripristino database da: $BackupDir"
    $confirmation = Read-Host "Sei sicuro? Questo sovrascriverà il database esistente [y/N]"
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        $mongoContainer = docker-compose ps -q mongo
        docker cp "./backups/$BackupDir" "${mongoContainer}:/tmp/"
        docker-compose exec mongo mongorestore --db tradingview_clone --drop "/tmp/$BackupDir/tradingview_clone"
        Write-Success "Database ripristinato!"
    } else {
        Write-Info "Operazione annullata"
    }
}

# Main switch
switch ($Command) {
    "dev" { Start-Dev }
    "prod" { Start-Prod }
    "build" { Build-Images }
    "clean" { Clean-All }
    "logs" { Show-Logs $Service }
    "restart" { Restart-Services }
    "stop" { Stop-Services }
    "status" { Show-Status }
    "shell-backend" { Shell-Backend }
    "shell-frontend" { Shell-Frontend }
    "backup-db" { Backup-Database }
    "restore-db" { Restore-Database $Service }
    { $_ -in @("help", "--help", "-h", "") } { Show-Help }
    default {
        Write-Error-Custom "Comando non riconosciuto: $Command"
        Show-Help
    }
}
