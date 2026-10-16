# Script de PowerShell para configurar el Worker como Servicio de Windows via NSSM (ADR-0001, ADR-0007)
param(
    [string]$ServiceName = "BoticaLaLuzWorker",
    [string]$PythonExe = "python.exe",
    [string]$AppRoot = (Resolve-Path "$PSScriptRoot\..\backend").Path
)

Write-Host "Configurando servicio Windows supervisado para los workers en: $AppRoot" -ForegroundColor Cyan

# Comprobar si NSSM esta disponible en PATH
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Warning "NSSM no encontrado en PATH. Instale nssm via scoop ('scoop install nssm') o descarguelo para continuar."
    exit 1
}

# Comandos de configuracion con NSSM
nssm install $ServiceName $PythonExe "-m src.workers.main"
nssm set $ServiceName AppDirectory $AppRoot
nssm set $ServiceName AppStdout "$AppRoot\..\logs\worker-stdout.log"
nssm set $ServiceName AppStderr "$AppRoot\..\logs\worker-stderr.log"
nssm set $ServiceName Start SERVICE_AUTO_START

Write-Host "Servicio '$ServiceName' configurado exitosamente." -ForegroundColor Green
Write-Host "Para iniciar el servicio ejecute: Start-Service $ServiceName (o nssm start $ServiceName)"
