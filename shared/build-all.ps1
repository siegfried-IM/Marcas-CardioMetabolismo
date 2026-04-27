#requires -Version 5.1
<#
.SYNOPSIS
  Orquestador para regenerar los data.js de todos los dashboards del repo.

.DESCRIPTION
  Corre los build-data.ps1 de cardio, ATB, OTC, mujer y respiratorio para
  un mes dado, leyendo los Excels desde Hub-Marcas-Inputs (en OneDrive) y
  escribiendo el data.js de cada linea en su carpeta del repo.

  Lineas sin Excels en su carpeta del mes se saltean con warning.

.PARAMETER Month
  Mes a procesar en formato YYYY-MM, ej: '2026-04'.

.PARAMETER BaseDir
  Raiz de Hub-Marcas-Inputs. Por default usa
  $env:OneDrive\Documentos\Hub-Marcas-Inputs.

.PARAMETER Lines
  Lineas a procesar. Por default 'all' (cardio, ATB, OTC, mujer, respiratorio).
  Pueden pasarse varias separadas por coma: -Lines cardio,ATB

.PARAMETER CommitPush
  Si esta presente, hace git add */data.js + commit + push a origin/main.

.PARAMETER CommitMessage
  Mensaje de commit. Default: "Update dashboard data for <Month> cut".

.PARAMETER DryRun
  No corre ningun build, solo imprime que harian.

.PARAMETER IqviaSubfolder
  Subcarpeta dentro de BaseDir donde esta el Excel maestro de IQVIA.
  Default: '_iqvia-master'. Path final: <BaseDir>/<IqviaSubfolder>/<Month>/.
  Si la carpeta no existe, cada linea cae al lookup legacy en sus propias fuentes.

.PARAMETER IqviaPattern
  Glob para encontrar el Excel maestro de IQVIA dentro de la carpeta IqviaSubfolder.
  Default: 'AR PM*'. Solo se usa si la carpeta IqviaSubfolder existe.

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04'
  Regenera data.js de las 5 lineas para el corte 2026-04. No hace commit.
  Lee el PM IQVIA desde Hub-Marcas-Inputs/_iqvia-master/2026-04/AR PM*.xlsx
  si existe, sino cada linea cae al lookup legacy.

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04' -Lines cardio,ATB
  Solo regenera cardio y ATB.

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04' -CommitPush
  Regenera todo y pushea a origin/main (Cloudflare Pages re-deploya solo).

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04' -DryRun
  Muestra que builds correrian sin ejecutar nada.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^\d{4}-\d{2}$')]
    [string]$Month,

    [string]$BaseDir = (Join-Path $env:OneDrive 'Documentos\Hub-Marcas-Inputs'),

    [ValidateSet('cardio','ATB','OTC','mujer','respiratorio','all')]
    [string[]]$Lines = @('all'),

    [switch]$CommitPush,

    [string]$CommitMessage,

    [switch]$DryRun,

    [string]$IqviaSubfolder = '_iqvia-master',

    [string]$IqviaPattern = 'AR PM*'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

# Mapeo: linea repo -> carpeta hub + subcarpeta de fuentes
# La subcarpeta '' significa que el script lee de la raiz del mes (caso respiratorio).
$lineConfig = [ordered]@{
    'cardio'       = @{ HubFolder = 'cardio';       FuentesSub = 'fuentes-originales' }
    'ATB'          = @{ HubFolder = 'ATB';          FuentesSub = 'fuentes-originales' }
    'OTC'          = @{ HubFolder = 'OTC';          FuentesSub = 'fuentes-originales' }
    'mujer'        = @{ HubFolder = 'linea-mujer';  FuentesSub = 'fuentes-originales' }
    'respiratorio' = @{ HubFolder = 'respiratorio'; FuentesSub = '' }
}

if ($Lines -contains 'all') {
    $Lines = @($lineConfig.Keys)
}

if (-not $CommitMessage) {
    $CommitMessage = "Update dashboard data for $Month cut"
}

# Validacion del BaseDir
if (-not (Test-Path -LiteralPath $BaseDir)) {
    throw "BaseDir not found: $BaseDir`nUsa -BaseDir <path> si tu Hub-Marcas-Inputs esta en otro lugar."
}

# IQVIA centralizada (opcional). Si la carpeta no existe, cada linea
# cae al lookup legacy en su propia carpeta de fuentes.
$iqviaMasterDir = Join-Path $BaseDir (Join-Path $IqviaSubfolder $Month)
$iqviaCentralized = Test-Path -LiteralPath $iqviaMasterDir
if ($iqviaCentralized) {
    $iqviaFile = Get-ChildItem -LiteralPath $iqviaMasterDir -Filter $IqviaPattern -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $iqviaFile) {
        Write-Warning "Carpeta IQVIA centralizada existe pero no hay match para '$IqviaPattern' en $iqviaMasterDir. Cae a legacy."
        $iqviaCentralized = $false
    }
}

Write-Host ""
Write-Host "================================================================"
Write-Host " build-all  -  Mes: $Month  -  Lineas: $($Lines -join ', ')"
Write-Host " Hub:  $BaseDir"
Write-Host " Repo: $repoRoot"
if ($iqviaCentralized) {
    Write-Host " IQVIA: $iqviaMasterDir  (pattern '$IqviaPattern')" -ForegroundColor Green
} else {
    Write-Host " IQVIA: legacy (cada linea lee de su carpeta de fuentes)" -ForegroundColor DarkGray
}
if ($DryRun) { Write-Host " ** DRY RUN ** (no se ejecuta nada)" }
Write-Host "================================================================"

$results = [ordered]@{}

foreach ($line in $Lines) {
    if (-not $lineConfig.Contains($line)) {
        Write-Warning "Linea desconocida: $line  -  saltando"
        $results[$line] = 'unknown'
        continue
    }
    $cfg = $lineConfig[$line]
    $monthDir = Join-Path $BaseDir (Join-Path $cfg.HubFolder $Month)
    if ($cfg.FuentesSub) {
        $sourceDir = Join-Path $monthDir $cfg.FuentesSub
    } else {
        $sourceDir = $monthDir
    }
    $scriptPath = Join-Path $repoRoot (Join-Path $line 'build-data.ps1')

    Write-Host ""
    Write-Host "[$line] -----------------------------------------------------" -ForegroundColor Cyan
    Write-Host "  Source:  $sourceDir"
    Write-Host "  Script:  $scriptPath"

    if (-not (Test-Path -LiteralPath $sourceDir)) {
        Write-Warning "  Carpeta de fuentes inexistente. Saltando."
        $results[$line] = 'skipped (no source folder)'
        continue
    }
    $excelCount = (Get-ChildItem -LiteralPath $sourceDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.xlsx','.xlsm','.xls','.csv' }).Count
    if ($excelCount -eq 0) {
        Write-Warning "  No hay Excels/CSV en la carpeta. Saltando."
        $results[$line] = 'skipped (empty)'
        continue
    }
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        Write-Warning "  Script de build inexistente: $scriptPath"
        $results[$line] = 'skipped (no script)'
        continue
    }

    # Build args para la invocacion
    $invokeArgs = @{ SourceDir = $sourceDir }
    if ($iqviaCentralized) {
        $invokeArgs.IqviaDir = $iqviaMasterDir
        $invokeArgs.IqviaPattern = $IqviaPattern
    }

    if ($DryRun) {
        $argsPreview = $invokeArgs.GetEnumerator() | ForEach-Object { "-$($_.Key) `"$($_.Value)`"" }
        Write-Host "  [DRY RUN] $scriptPath $($argsPreview -join ' ')" -ForegroundColor Yellow
        $results[$line] = 'dry-run'
        continue
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        & $scriptPath @invokeArgs
        $sw.Stop()
        $results[$line] = "ok ($([int]$sw.Elapsed.TotalSeconds)s)"
        Write-Host "  OK ($([int]$sw.Elapsed.TotalSeconds)s)" -ForegroundColor Green
    } catch {
        $sw.Stop()
        $msg = $_.Exception.Message
        if ($msg.Length -gt 200) { $msg = $msg.Substring(0,200) + '...' }
        $results[$line] = "FAILED: $msg"
        Write-Host "  FAILED: $msg" -ForegroundColor Red
    }
}

# Resumen
Write-Host ""
Write-Host "================================================================"
Write-Host " RESUMEN"
Write-Host "================================================================"
foreach ($k in $results.Keys) {
    $status = $results[$k]
    $color = switch -Wildcard ($status) {
        'ok*'        { 'Green' }
        'skipped*'   { 'Yellow' }
        'unknown'    { 'Yellow' }
        'dry-run'    { 'DarkGray' }
        'FAILED*'    { 'Red' }
        default      { 'Gray' }
    }
    Write-Host ("  {0,-14} : {1}" -f $k, $status) -ForegroundColor $color
}

# Commit & push
if ($CommitPush -and -not $DryRun) {
    $hadFailure = $results.Values | Where-Object { $_ -like 'FAILED*' }
    if ($hadFailure) {
        Write-Host ""
        Write-Warning "Hubo errores en algun build, NO se hace commit/push."
        exit 1
    }
    Write-Host ""
    Write-Host "================================================================"
    Write-Host " Git commit + push"
    Write-Host "================================================================"
    Push-Location $repoRoot
    try {
        git add '*/data.js' 2>&1 | Out-Null
        $staged = git diff --cached --name-only
        if (-not $staged) {
            Write-Host "  Sin cambios para commitear." -ForegroundColor Yellow
        } else {
            Write-Host "  Archivos staged:"
            $staged | ForEach-Object { Write-Host "    $_" }
            git commit -m $CommitMessage
            if ($LASTEXITCODE -ne 0) { throw "git commit fallo (exit $LASTEXITCODE)" }
            git push origin main
            if ($LASTEXITCODE -ne 0) { throw "git push fallo (exit $LASTEXITCODE)" }
            Write-Host "  Pusheado a origin/main." -ForegroundColor Green
            Write-Host "  Cloudflare Pages re-deploya en ~1-2 min." -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

Write-Host ""
