$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot '.demo-runtime\procesos.json'
if (!(Test-Path -LiteralPath $pidFile)) { Write-Host 'No hay servicios registrados por Iniciar-Demo.ps1.'; return }
$records = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($record in $records) {
    $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $record.ticks -and $process.Path -eq $record.executable) {
        Stop-Process -InputObject $process
    }
}
Remove-Item -LiteralPath $pidFile
Write-Host 'Servicios de demostración detenidos. Los datos ficticios se reiniciarán en el siguiente arranque.'
