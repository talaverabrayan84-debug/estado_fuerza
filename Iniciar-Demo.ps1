param([string]$PythonPath = '')
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.demo-runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$pidFile = Join-Path $runtimeDir 'procesos.json'
if (Test-Path -LiteralPath $pidFile) { throw 'Primero ejecuta Detener-Demo.ps1 para cerrar la demostración anterior.' }
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (!$nodeCommand -or !$npmCommand) { throw 'Instala Node.js 22 o posterior y vuelve a ejecutar el script.' }
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $venvPython)) {
    if (!$PythonPath) {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($pythonCommand) { $PythonPath = $pythonCommand.Source }
        else { $PythonPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' }
    }
    if (!(Test-Path -LiteralPath $PythonPath)) { throw 'Instala Python 3.11 o posterior, o pasa -PythonPath con la ruta de python.exe.' }
    & $PythonPath -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de Python.' }
}
$pythonLock = Join-Path $projectRoot 'backend\requirements-lock.txt'
$pythonHash = (Get-FileHash -LiteralPath $pythonLock -Algorithm SHA256).Hash
$pythonMarker = Join-Path $runtimeDir 'python-instalado'
if (!(Test-Path -LiteralPath $pythonMarker) -or (Get-Content -LiteralPath $pythonMarker -Raw).Trim() -ne $pythonHash) {
    & $venvPython -m pip install -r (Join-Path $projectRoot 'backend\requirements-lock.txt')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de Python.' }
    Set-Content -LiteralPath $pythonMarker -Value $pythonHash
}
$frontendDir = Join-Path $projectRoot 'frontend'
if (!(Test-Path -LiteralPath (Join-Path $frontendDir 'node_modules'))) {
    Push-Location -LiteralPath $frontendDir
    try { & $npmCommand.Source ci; if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de la interfaz.' } }
    finally { Pop-Location }
}
$demoEnv = @{ APP_ENV='development'; DEMO_MODE='true'; VITE_DEMO_MODE='true'; VITE_API_URL='http://127.0.0.1:8000/api'; FRONTEND_ORIGINS='http://localhost:5173,http://127.0.0.1:5173' }
$previousEnv = @{}
$started = @()
try {
    foreach ($key in $demoEnv.Keys) { $previousEnv[$key] = [Environment]::GetEnvironmentVariable($key,'Process'); [Environment]::SetEnvironmentVariable($key,$demoEnv[$key],'Process') }
    Push-Location -LiteralPath $frontendDir
    try { & $npmCommand.Source run build -- --outDir ../.demo-runtime/web; if ($LASTEXITCODE -ne 0) { throw 'No se pudo compilar la demostración.' } }
    finally { Pop-Location }
    $apiProcess = Start-Process -FilePath $venvPython -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir 'backend.log') -RedirectStandardError (Join-Path $runtimeDir 'backend-error.log')
    $started += $apiProcess
    $vitePath = Join-Path $frontendDir 'node_modules\vite\bin\vite.js'
    $webProcess = Start-Process -FilePath $nodeCommand.Source -ArgumentList @(('"' + $vitePath + '"'),'preview','--outDir','../.demo-runtime/web','--host','127.0.0.1','--port','5173','--strictPort','--configLoader','runner') -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend-error.log')
    $started += $webProcess
    $available = $false
    for ($i=0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 500
        $apiProcess.Refresh(); $webProcess.Refresh()
        if ($apiProcess.HasExited -or $webProcess.HasExited) { throw "Un servicio no pudo iniciar. Revisa los archivos de $runtimeDir (por ejemplo, si los puertos están ocupados)." }
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2
            $page = Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2
            if ($health.mode -eq 'demo' -and $page.StatusCode -eq 200) { $available=$true; break }
        } catch { }
    }
    if (!$available) { throw "No se confirmó el arranque. Revisa los archivos de $runtimeDir." }
    @($started | ForEach-Object { @{ id=$_.Id; ticks=$_.StartTime.ToUniversalTime().Ticks; executable=$_.Path } }) | ConvertTo-Json | Set-Content -LiteralPath $pidFile
    Write-Host 'Demostración disponible en http://127.0.0.1:5173'
    Write-Host 'Selecciona Administrador, Gestor de capacitación o Trabajador en la pantalla de acceso.'
    Write-Host 'Para detener los servicios ejecuta .\Detener-Demo.ps1.'
} catch {
    foreach ($process in $started) { if (!$process.HasExited) { Stop-Process -InputObject $process -ErrorAction SilentlyContinue } }
    throw
} finally {
    foreach ($key in $previousEnv.Keys) { [Environment]::SetEnvironmentVariable($key,$previousEnv[$key],'Process') }
}
