# Actividad 5 — Flujo en tiempo real: CounterFit + TimescaleDB + dashboard.
# Ejecutar desde la raiz: .\actividad5\activar_flujo.ps1

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$samples = 1440   # 2 horas x 3600 s / 5 s

if (-not (Test-Path "$root\.venv\Scripts\python.exe")) {
    Write-Error "No se encontro .venv."
    exit 1
}

Write-Host "Sembrando datos de mayo en TimescaleDB (opcional, para filtros)..." -ForegroundColor Cyan
& "$root\.venv\Scripts\python.exe" "$root\actividad4\sembrar_datos_mayo.py"

Write-Host "Abriendo 3 terminales (captura 2 h cada 5 s, dashboard refresh 30 s)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\.venv\Scripts\counterfit --port 5050"
Start-Sleep -Seconds 3
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\.venv\Scripts\python actividad4\nodo_timescale.py --port 5050 --interval-sec 5 --samples $samples"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\.venv\Scripts\streamlit run actividad4\dashboard_iot.py"

Write-Host "Dashboard: http://localhost:8501" -ForegroundColor Green
