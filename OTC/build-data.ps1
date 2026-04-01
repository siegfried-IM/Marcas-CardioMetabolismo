param(
  [string]$SourceDir = 'C:\Users\camarinaro\Downloads\Actualizaciones-Marcas\OTC\2026-04\fuentes-originales',
  [string]$OutputPath = (Join-Path $PSScriptRoot 'data.js')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$monthIndex = @{
  'ene' = 1; 'feb' = 2; 'mar' = 3; 'abr' = 4; 'may' = 5; 'jun' = 6
  'jul' = 7; 'ago' = 8; 'sep' = 9; 'sept' = 9; 'oct' = 10; 'nov' = 11; 'dic' = 12
}

$monthLabel = @{
  1 = 'Ene'; 2 = 'Feb'; 3 = 'Mar'; 4 = 'Abr'; 5 = 'May'; 6 = 'Jun'
  7 = 'Jul'; 8 = 'Ago'; 9 = 'Sep'; 10 = 'Oct'; 11 = 'Nov'; 12 = 'Dic'
}

$familyOrder = @(
  'Totales',
  'ACERPES',
  'ACI-TIP',
  'ALUMPAK',
  'ARTRO RED',
  'FLEXINA',
  'MAGNUS',
  'TETRALGIN',
  'TETRALGIN NOVO'
)

$dddMarketConfig = [ordered]@{
  'Acerpes Comp.' = @{ family = 'ACERPES'; keywords = @('ACERPES') }
  'Acerpes Crema' = @{ family = 'ACERPES'; keywords = @('ACERPES') }
  'Artro Red' = @{ family = 'ARTRO RED'; keywords = @('ARTRO RED') }
  'Flexina 600' = @{ family = 'FLEXINA'; keywords = @('FLEXINA') }
  'Magnus' = @{ family = 'MAGNUS'; keywords = @('MAGNUS') }
  'Magnus 36' = @{ family = 'MAGNUS'; keywords = @('MAGNUS') }
  'Tetralgin' = @{ family = 'TETRALGIN'; keywords = @('TETRALGIN') }
}

function Get-MatchingPath {
  param(
    [string]$Dir,
    [string]$Include,
    [string]$Exclude = ''
  )

  $items = Get-ChildItem -LiteralPath $Dir | Where-Object { $_.Name -like $Include }
  if ($Exclude) {
    $items = $items | Where-Object { $_.Name -notlike $Exclude }
  }

  $match = $items | Select-Object -First 1
  if (-not $match) {
    throw "No se encontro un archivo que coincida con '$Include' en '$Dir'."
  }

  return $match.FullName
}

function Normalize-Text {
  param([object]$Value)

  if ($null -eq $Value) {
    return ''
  }

  return ([string]$Value).Trim()
}

function To-Number {
  param([object]$Value)

  if ($null -eq $Value) {
    return 0.0
  }

  if ($Value -is [double] -or $Value -is [single] -or $Value -is [decimal] -or
      $Value -is [int] -or $Value -is [long]) {
    return [double]$Value
  }

  $text = ([string]$Value).Trim()
  if (-not $text -or $text -eq '-') {
    return 0.0
  }

  $parsed = 0.0
  if ([double]::TryParse($text, [System.Globalization.NumberStyles]::Any, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
    return $parsed
  }

  $text = $text.Replace('.', '').Replace('%', '').Replace(',', '.')
  if ([double]::TryParse($text, [System.Globalization.NumberStyles]::Any, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
    return $parsed
  }

  return 0.0
}

function Normalize-MonthLabel {
  param([object]$Value)

  if ($Value -is [double] -or $Value -is [single] -or $Value -is [decimal] -or
      $Value -is [int] -or $Value -is [long]) {
    try {
      $date = [datetime]::FromOADate([double]$Value)
      return '{0}-{1}' -f $monthLabel[$date.Month], $date.Year
    }
    catch {
    }
  }

  $raw = Normalize-Text $Value
  if (-not $raw) {
    return ''
  }

  if ($raw -match '^([A-Za-z]+)-(\d{4})$') {
    $mon = $matches[1].ToLower()
    $year = [int]$matches[2]
    if ($monthIndex.ContainsKey($mon)) {
      return '{0}-{1}' -f $monthLabel[$monthIndex[$mon]], $year
    }
  }

  return $raw
}

function Get-MonthSortValue {
  param([string]$Label)

  if ($Label -match '^([A-Za-z]+)-(\d{4})$') {
    $mon = $matches[1].ToLower()
    $year = [int]$matches[2]
    if ($monthIndex.ContainsKey($mon)) {
      return ($year * 100) + $monthIndex[$mon]
    }
  }

  return 0
}

function Sort-Months {
  param([string[]]$Months)

  return $Months | Sort-Object { Get-MonthSortValue $_ }
}

function Round-Number {
  param(
    [double]$Value,
    [int]$Digits = 1
  )

  return [math]::Round($Value, $Digits)
}

function Ensure-Map {
  param(
    [hashtable]$Map,
    [string]$Key
  )

  if (-not $Map.ContainsKey($Key)) {
    $Map[$Key] = @{}
  }
}

function Ensure-OrderedMap {
  param(
    [System.Collections.Specialized.OrderedDictionary]$Map,
    [string]$Key,
    [object]$Value
  )

  if (-not $Map.Contains($Key)) {
    $Map.Add($Key, $Value)
  }
}

function Ensure-NestedMetric {
  param(
    [hashtable]$Map,
    [string]$Key
  )

  if (-not $Map.ContainsKey($Key)) {
    $Map[$Key] = @{
      total = 0.0
      sie = 0.0
    }
  }
}

function Get-LastNonZeroMonth {
  param(
    [string[]]$Months,
    [double[]]$Values
  )

  for ($i = $Values.Count - 1; $i -ge 0; $i--) {
    if ($Values[$i] -gt 0) {
      return $Months[$i]
    }
  }

  return ''
}

function Get-YtdSum {
  param(
    [string[]]$Months,
    [double[]]$Values,
    [int]$Year,
    [string]$CutMonth
  )

  $cutValue = Get-MonthSortValue $CutMonth
  $sum = 0.0
  for ($i = 0; $i -lt $Months.Count; $i++) {
    if ($Months[$i] -match "-$Year$" -and (Get-MonthSortValue $Months[$i]) -le $cutValue) {
      $sum += $Values[$i]
    }
  }

  return [math]::Round($sum, 0)
}

function Convert-MetricMap {
  param([hashtable]$Map)

  $rows = foreach ($key in ($Map.Keys | Sort-Object)) {
    $item = $Map[$key]
    $share = if ($item.total -gt 0) { Round-Number (($item.sie / $item.total) * 100) } else { 0.0 }
    [pscustomobject][ordered]@{
      name = $key
      total = [math]::Round($item.total, 0)
      sie = [math]::Round($item.sie, 0)
      share = $share
    }
  }

  return @($rows)
}

if (-not (Test-Path -LiteralPath $SourceDir)) {
  throw "La carpeta de fuentes no existe: $SourceDir"
}

$budgetPath = Get-MatchingPath -Dir $SourceDir -Include 'Sin*Tabla din*2026.xlsx' -Exclude '*(1)*'
$rxMatch = Get-ChildItem -LiteralPath $SourceDir | Where-Object { $_.Name -like 'Sin*Tabla din*2026*' -and $_.Name -like '*(1)*' } | Select-Object -First 1
if (-not $rxMatch) {
  throw "No se encontro la base de recetas/medicos de OTC."
}
$rxPath = $rxMatch.FullName
$stockPath = Get-MatchingPath -Dir $SourceDir -Include 'Laboratorio - Familia - Producto*'
$channelPath = Get-MatchingPath -Dir $SourceDir -Include 'Convenios vs mostrador*'
$conv2024Path = Get-MatchingPath -Dir $SourceDir -Include 'Detalle consumos y aportes por convenio - periodo 2024*'
$conv2025Path = Get-MatchingPath -Dir $SourceDir -Include 'Detalle consumos y aportes por convenio - periodo 2025*'
$dddPath = Get-MatchingPath -Dir $SourceDir -Include 'Producto-Mol*provincia*'

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

function Open-Matrix {
  param(
    [object]$Excel,
    [string]$Path
  )

  $ws = $null
  $usedRange = $null
  $wb = $Excel.Workbooks.Open($Path)
  try {
    $ws = $wb.Worksheets.Item(1)
    $usedRange = $ws.UsedRange
    $value = $usedRange.Value2
    return ,$value
  }
  finally {
    if ($null -ne $usedRange) {
      [System.Runtime.InteropServices.Marshal]::ReleaseComObject($usedRange) | Out-Null
    }
    if ($null -ne $ws) {
      [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ws) | Out-Null
    }
    $wb.Close($false)
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null
  }
}

try {
  $budgetMatrix = Open-Matrix -Excel $excel -Path $budgetPath
  $rxMatrix = Open-Matrix -Excel $excel -Path $rxPath
  $stockMatrix = Open-Matrix -Excel $excel -Path $stockPath
  $channelMatrix = Open-Matrix -Excel $excel -Path $channelPath
  $conv2024Matrix = Open-Matrix -Excel $excel -Path $conv2024Path
  $conv2025Matrix = Open-Matrix -Excel $excel -Path $conv2025Path
  $dddMatrix = Open-Matrix -Excel $excel -Path $dddPath
}
finally {
  $excel.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}

$budgetMonths = @()
for ($c = 3; $c -le $budgetMatrix.GetLength(1); $c += 3) {
  $budgetMonths += Normalize-MonthLabel $budgetMatrix[1, $c]
}

$budgetFamilies = [ordered]@{}
$budgetProducts = [ordered]@{}
for ($r = 3; $r -le $budgetMatrix.GetLength(0); $r++) {
  $family = Normalize-Text $budgetMatrix[$r, 1]
  $product = Normalize-Text $budgetMatrix[$r, 2]
  if (-not $family) {
    continue
  }

  $actual = New-Object System.Collections.Generic.List[double]
  $budget = New-Object System.Collections.Generic.List[double]
  $compliance = New-Object System.Collections.Generic.List[double]

  for ($c = 3; $c -le $budgetMatrix.GetLength(1); $c += 3) {
    $actual.Add((To-Number $budgetMatrix[$r, $c]))
    $budget.Add((To-Number $budgetMatrix[$r, ($c + 1)]))
    $compliance.Add((Round-Number ((To-Number $budgetMatrix[$r, ($c + 2)]) * 100)))
  }

  if ($family -eq 'Totales' -or $product -eq 'Totales' -or -not $product) {
    Ensure-OrderedMap -Map $budgetFamilies -Key $family -Value ([ordered]@{
      actual = @($actual)
      budget = @($budget)
      compliance = @($compliance)
    })
    continue
  }

  if (-not $budgetProducts.Contains($family)) {
    $budgetProducts.Add($family, @())
  }

  $latestIndex = $actual.Count - 1
  while ($latestIndex -ge 0 -and $actual[$latestIndex] -le 0) {
    $latestIndex--
  }

  $budgetProducts[$family] += [pscustomobject][ordered]@{
    name = $product
    totalActual = [math]::Round(($actual | Measure-Object -Sum).Sum, 0)
    ytd2026 = Get-YtdSum -Months $budgetMonths -Values @($actual) -Year 2026 -CutMonth (Get-LastNonZeroMonth -Months $budgetMonths -Values @($actual))
    latestActual = if ($latestIndex -ge 0) { [math]::Round($actual[$latestIndex], 0) } else { 0 }
  }
}

$budgetCut = Get-LastNonZeroMonth -Months $budgetMonths -Values $budgetFamilies['Totales'].actual
foreach ($family in @($budgetProducts.Keys)) {
  $budgetProducts[$family] = @(
    $budgetProducts[$family] |
      Sort-Object -Property @{ Expression = 'ytd2026'; Descending = $true }, @{ Expression = 'totalActual'; Descending = $true } |
      Select-Object -First 8
  )
}

$stockMonths = @()
for ($c = 8; $c -le $stockMatrix.GetLength(1); $c += 4) {
  $stockMonths += Normalize-MonthLabel $stockMatrix[1, $c]
}

$stockFamilies = [ordered]@{}
$stockProducts = [ordered]@{}
for ($r = 3; $r -le $stockMatrix.GetLength(0); $r++) {
  $family = Normalize-Text $stockMatrix[$r, 2]
  $product = Normalize-Text $stockMatrix[$r, 3]
  if (-not $family) {
    continue
  }

  $stockSeries = New-Object System.Collections.Generic.List[double]
  $salesSeries = New-Object System.Collections.Generic.List[double]
  $billingSeries = New-Object System.Collections.Generic.List[double]
  $daysSeries = New-Object System.Collections.Generic.List[double]

  for ($c = 8; $c -le $stockMatrix.GetLength(1); $c += 4) {
    $stockSeries.Add((To-Number $stockMatrix[$r, $c]))
    $salesSeries.Add((To-Number $stockMatrix[$r, ($c + 1)]))
    $billingSeries.Add((To-Number $stockMatrix[$r, ($c + 2)]))
    $daysSeries.Add((To-Number $stockMatrix[$r, ($c + 3)]))
  }

  if ($family -eq 'Totales' -or $product -eq 'Totales' -or -not $product) {
    Ensure-OrderedMap -Map $stockFamilies -Key $family -Value ([ordered]@{
      stock = @($stockSeries)
      sales = @($salesSeries)
      billing = @($billingSeries)
      days = @($daysSeries)
    })
    continue
  }

  if (-not $stockProducts.Contains($family)) {
    $stockProducts.Add($family, @())
  }

  $stockProducts[$family] += [pscustomobject][ordered]@{
    name = $product
    totalStock = [math]::Round((To-Number $stockMatrix[$r, 4]), 0)
    totalSales = [math]::Round((To-Number $stockMatrix[$r, 5]), 0)
    totalBilling = [math]::Round((To-Number $stockMatrix[$r, 6]), 0)
    totalDays = [math]::Round((To-Number $stockMatrix[$r, 7]), 0)
  }
}

$stockCut = Get-LastNonZeroMonth -Months $stockMonths -Values $stockFamilies['Totales'].sales
foreach ($family in @($stockProducts.Keys)) {
  $stockProducts[$family] = @(
    $stockProducts[$family] |
      Sort-Object -Property @{ Expression = 'totalSales'; Descending = $true }, @{ Expression = 'totalBilling'; Descending = $true } |
      Select-Object -First 8
  )
}

$channelFamilies = [ordered]@{}
for ($r = 2; $r -le $channelMatrix.GetLength(0); $r++) {
  $family = Normalize-Text $channelMatrix[$r, 2]
  if (-not $family) {
    continue
  }

  $units = To-Number $channelMatrix[$r, 5]
  $convenioUnits = To-Number $channelMatrix[$r, 8]
  $mostradorUnits = $units - $convenioUnits

  Ensure-OrderedMap -Map $channelFamilies -Key $family -Value ([ordered]@{
    facturedUnits = [math]::Round($units, 0)
    convenioUnits = [math]::Round($convenioUnits, 0)
    mostradorUnits = [math]::Round($mostradorUnits, 0)
    convenioPct = Round-Number ((To-Number $channelMatrix[$r, 12]) * 100)
    mostradorPct = Round-Number ((To-Number $channelMatrix[$r, 13]) * 100)
    discountCommonPct = Round-Number ((To-Number $channelMatrix[$r, 14]) * 100)
    discountConvenioPct = Round-Number ((To-Number $channelMatrix[$r, 15]) * 100)
    discountTotalPct = Round-Number ((To-Number $channelMatrix[$r, 16]) * 100)
  })
}

$osAggregate = @{}
foreach ($family in $familyOrder) {
  $osAggregate[$family] = @{}
}
$osAggregate['Totales'] = @{}

foreach ($rowSet in @(
  @{ year = 2024; matrix = $conv2024Matrix },
  @{ year = 2025; matrix = $conv2025Matrix }
)) {
  $year = $rowSet.year
  $matrix = $rowSet.matrix

  for ($r = 2; $r -le $matrix.GetLength(0); $r++) {
    $family = Normalize-Text $matrix[$r, 3]
    $os = Normalize-Text $matrix[$r, 4]
    if (-not $family -or -not $os) {
      continue
    }

    $units = To-Number $matrix[$r, 5]
    foreach ($bucket in @($family, 'Totales')) {
      if (-not $osAggregate.ContainsKey($bucket)) {
        $osAggregate[$bucket] = @{}
      }
      if (-not $osAggregate[$bucket].ContainsKey($os)) {
        $osAggregate[$bucket][$os] = @{ units2024 = 0.0; units2025 = 0.0 }
      }
      if ($year -eq 2024) {
        $osAggregate[$bucket][$os].units2024 += $units
      }
      else {
        $osAggregate[$bucket][$os].units2025 += $units
      }
    }
  }
}

$osFamilies = [ordered]@{}
foreach ($family in ($osAggregate.Keys | Sort-Object { $familyOrder.IndexOf($_) })) {
  $rows = foreach ($os in $osAggregate[$family].Keys) {
    $item = $osAggregate[$family][$os]
    $deltaUnits = $item.units2025 - $item.units2024
    [pscustomobject][ordered]@{
      os = $os
      units2024 = [math]::Round($item.units2024, 0)
      units2025 = [math]::Round($item.units2025, 0)
      deltaUnits = [math]::Round($deltaUnits, 0)
    }
  }

  $total2025 = (($rows | ForEach-Object { [double]$_.units2025 } | Measure-Object -Sum).Sum)
  $prepared = @(
    $rows |
      Sort-Object -Property @{ Expression = 'units2025'; Descending = $true } |
      Select-Object -First 10 |
      ForEach-Object {
        $share = if ($total2025 -gt 0) { Round-Number (($_.units2025 / $total2025) * 100) } else { 0.0 }
        $deltaPct = if ($_.units2024 -gt 0) { Round-Number (((($_.units2025 - $_.units2024) / $_.units2024) * 100)) } else { 0.0 }
        [pscustomobject][ordered]@{
          os = $_.os
          units2024 = $_.units2024
          units2025 = $_.units2025
          share2025 = $share
          deltaUnits = $_.deltaUnits
          deltaPct = $deltaPct
        }
      }
  )

  Ensure-OrderedMap -Map $osFamilies -Key $family -Value ([ordered]@{
    total2025 = [math]::Round($total2025, 0)
    rows = $prepared
  })
}

$rxMonths = @()
for ($c = 4; $c -le $rxMatrix.GetLength(1); $c += 2) {
  $rxMonths += Normalize-MonthLabel $rxMatrix[1, $c]
}

$rxFamilies = @{}
$rxBrands = @{}
for ($r = 3; $r -le $rxMatrix.GetLength(0); $r++) {
  $market = Normalize-Text $rxMatrix[$r, 1]
  $drug = Normalize-Text $rxMatrix[$r, 2]
  $brand = Normalize-Text $rxMatrix[$r, 3]
  if (-not $market) {
    continue
  }

  $family = ''
  if ($market -match '\(([^)]+)\)') {
    $family = $matches[1].Trim().ToUpper()
  }
  else {
    $family = $market.ToUpper()
    if ($family -like 'FLEXINA*') { $family = 'FLEXINA' }
    if ($family -like 'MAGNUS*') { $family = 'MAGNUS' }
  }

  if (-not $rxFamilies.ContainsKey($family)) {
    $rxFamilies[$family] = @{
      prescriptions = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
      doctors = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
    }
  }

  if ($drug -eq 'Totales' -and -not $brand) {
    $index = 0
    for ($c = 4; $c -le $rxMatrix.GetLength(1); $c += 2) {
      $rxFamilies[$family].prescriptions[$index] += (To-Number $rxMatrix[$r, $c])
      $rxFamilies[$family].doctors[$index] += (To-Number $rxMatrix[$r, ($c + 1)])
      $index++
    }
    continue
  }

  if ($brand -and $brand -ne 'Totales') {
    if (-not $rxBrands.ContainsKey($family)) {
      $rxBrands[$family] = @{}
    }
    if (-not $rxBrands[$family].ContainsKey($brand)) {
      $rxBrands[$family][$brand] = @{ prescriptions = 0.0; doctors = 0.0 }
    }
    $rxBrands[$family][$brand].prescriptions += To-Number $rxMatrix[$r, ($rxMatrix.GetLength(1) - 1)]
    $rxBrands[$family][$brand].doctors += To-Number $rxMatrix[$r, $rxMatrix.GetLength(1)]
  }
}

$rxFamiliesOut = [ordered]@{}
foreach ($family in ($rxFamilies.Keys | Sort-Object { $familyOrder.IndexOf($_) })) {
  $series = $rxFamilies[$family]
  $latestMonth = Get-LastNonZeroMonth -Months $rxMonths -Values $series.prescriptions
  $brands = @()
  if ($rxBrands.ContainsKey($family)) {
    $brands = @(
      $rxBrands[$family].Keys |
        ForEach-Object {
          [pscustomobject][ordered]@{
            brand = $_
            prescriptions = [math]::Round($rxBrands[$family][$_].prescriptions, 0)
            doctors = [math]::Round($rxBrands[$family][$_].doctors, 0)
          }
        } |
        Sort-Object -Property @{ Expression = 'prescriptions'; Descending = $true } |
        Select-Object -First 8
    )
  }

  Ensure-OrderedMap -Map $rxFamiliesOut -Key $family -Value ([ordered]@{
    prescriptions = @($series.prescriptions | ForEach-Object { [math]::Round($_, 0) })
    doctors = @($series.doctors | ForEach-Object { [math]::Round($_, 0) })
    latestMonth = $latestMonth
    topBrands = $brands
  })
}

$rxTotals = @{
  prescriptions = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
  doctors = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
}
foreach ($family in $rxFamiliesOut.Keys) {
  if ($family -eq 'Totales') {
    continue
  }
  for ($i = 0; $i -lt $rxMonths.Count; $i++) {
    $rxTotals.prescriptions[$i] += $rxFamiliesOut[$family].prescriptions[$i]
    $rxTotals.doctors[$i] += $rxFamiliesOut[$family].doctors[$i]
  }
}
$rxFamiliesOut['Totales'] = [ordered]@{
  prescriptions = @($rxTotals.prescriptions | ForEach-Object { [math]::Round($_, 0) })
  doctors = @($rxTotals.doctors | ForEach-Object { [math]::Round($_, 0) })
  latestMonth = Get-LastNonZeroMonth -Months $rxMonths -Values $rxTotals.prescriptions
  topBrands = @()
}

$dddMonthsSet = New-Object 'System.Collections.Generic.HashSet[string]'
$dddMonthly = @{}
$dddRegions = @{}
$dddProducts = @{}

for ($r = 2; $r -le $dddMatrix.GetLength(0); $r++) {
  $market = Normalize-Text $dddMatrix[$r, 2]
  if (-not $dddMarketConfig.Contains($market)) {
    continue
  }

  $month = Normalize-MonthLabel $dddMatrix[$r, 5]
  $region = Normalize-Text $dddMatrix[$r, 1]
  $product = Normalize-Text $dddMatrix[$r, 8]
  $units = To-Number $dddMatrix[$r, 9]
  if (-not $month -or -not $region -or -not $product -or $units -le 0) {
    continue
  }

  $dddMonthsSet.Add($month) | Out-Null
  $isSie = $false
  foreach ($keyword in $dddMarketConfig[$market].keywords) {
    if ($product.ToUpper().Contains($keyword)) {
      $isSie = $true
      break
    }
  }

  if (-not $dddMonthly.ContainsKey($market)) {
    $dddMonthly[$market] = @{}
  }
  if (-not $dddRegions.ContainsKey($market)) {
    $dddRegions[$market] = @{}
  }
  if (-not $dddProducts.ContainsKey($market)) {
    $dddProducts[$market] = @{}
  }

  Ensure-NestedMetric -Map $dddMonthly[$market] -Key $month
  $dddMonthly[$market][$month].total += $units
  if ($isSie) {
    $dddMonthly[$market][$month].sie += $units
  }

  if (-not $dddRegions[$market].ContainsKey($month)) {
    $dddRegions[$market][$month] = @{}
  }
  Ensure-NestedMetric -Map $dddRegions[$market][$month] -Key $region
  $dddRegions[$market][$month][$region].total += $units
  if ($isSie) {
    $dddRegions[$market][$month][$region].sie += $units
  }

  if (-not $dddProducts[$market].ContainsKey($month)) {
    $dddProducts[$market][$month] = @{}
  }
  if (-not $dddProducts[$market][$month].ContainsKey($product)) {
    $dddProducts[$market][$month][$product] = @{
      units = 0.0
      isSie = $isSie
    }
  }
  $dddProducts[$market][$month][$product].units += $units
}

$dddMonths = Sort-Months @($dddMonthsSet)
$dddMarketsOut = [ordered]@{}

foreach ($market in $dddMarketConfig.Keys) {
  if (-not $dddMonthly.ContainsKey($market)) {
    continue
  }

  $monthlyRows = foreach ($month in $dddMonths) {
    $item = if ($dddMonthly[$market].ContainsKey($month)) { $dddMonthly[$market][$month] } else { @{ total = 0.0; sie = 0.0 } }
    $share = if ($item.total -gt 0) { Round-Number (($item.sie / $item.total) * 100) } else { 0.0 }
    [ordered]@{
      month = $month
      total = [math]::Round($item.total, 0)
      sie = [math]::Round($item.sie, 0)
      share = $share
    }
  }

  $latestMonth = $dddMonths[-1]
  $regionsByMonth = [ordered]@{}
  $productsByMonth = [ordered]@{}

  foreach ($month in $dddMonths) {
    $regionRows = @()
    if ($dddRegions[$market].ContainsKey($month)) {
      $regionRows = Convert-MetricMap $dddRegions[$market][$month]
    }
    $regionsByMonth.Add($month, @(
      $regionRows | Sort-Object -Property @{ Expression = 'share'; Descending = $true }, @{ Expression = 'total'; Descending = $true }
    ))

    $productRows = @()
    if ($dddProducts[$market].ContainsKey($month)) {
      $totalUnits = 0.0
      foreach ($name in $dddProducts[$market][$month].Keys) {
        $totalUnits += $dddProducts[$market][$month][$name].units
      }

      $productRows = @(
        $dddProducts[$market][$month].Keys |
          ForEach-Object {
            $item = $dddProducts[$market][$month][$_]
            [pscustomobject][ordered]@{
              product = $_
              units = [math]::Round($item.units, 0)
              share = if ($totalUnits -gt 0) { Round-Number (($item.units / $totalUnits) * 100) } else { 0.0 }
              isSie = [bool]$item.isSie
            }
          } |
          Sort-Object -Property @{ Expression = 'units'; Descending = $true } |
          Select-Object -First 12
      )
    }
    $productsByMonth.Add($month, $productRows)
  }

  $dddMarketsOut.Add($market, [ordered]@{
    family = $dddMarketConfig[$market].family
    latestMonth = $latestMonth
    monthly = $monthlyRows
    regionsByMonth = $regionsByMonth
    productsByMonth = $productsByMonth
  })
}

$dashboardShare = @{}
foreach ($family in $familyOrder) {
  $dashboardShare[$family] = @{}
}

foreach ($market in $dddMarketsOut.Keys) {
  $family = $dddMarketsOut[$market].family
  foreach ($row in $dddMarketsOut[$market].monthly) {
    if (-not $dashboardShare[$family].ContainsKey($row.month)) {
      $dashboardShare[$family][$row.month] = @{
        total = 0.0
        sie = 0.0
      }
    }
    $dashboardShare[$family][$row.month].total += $row.total
    $dashboardShare[$family][$row.month].sie += $row.sie
  }
}

$dashboardShareOut = [ordered]@{}
foreach ($family in $familyOrder) {
  if (-not $dashboardShare.ContainsKey($family)) {
    continue
  }
  $rows = foreach ($month in $dddMonths) {
    $item = if ($dashboardShare[$family].ContainsKey($month)) { $dashboardShare[$family][$month] } else { @{ total = 0.0; sie = 0.0 } }
    [ordered]@{
      month = $month
      total = [math]::Round($item.total, 0)
      sie = [math]::Round($item.sie, 0)
      share = if ($item.total -gt 0) { Round-Number (($item.sie / $item.total) * 100) } else { 0.0 }
    }
  }
  $dashboardShareOut.Add($family, $rows)
}

$dashboardShareOut['Totales'] = @(
  foreach ($month in $dddMonths) {
    $total = 0.0
    $sie = 0.0
    foreach ($family in $dashboardShareOut.Keys) {
      if ($family -eq 'Totales') {
        continue
      }
      $row = $dashboardShareOut[$family] | Where-Object { $_.month -eq $month } | Select-Object -First 1
      if ($row) {
        $total += $row.total
        $sie += $row.sie
      }
    }
    [ordered]@{
      month = $month
      total = [math]::Round($total, 0)
      sie = [math]::Round($sie, 0)
      share = if ($total -gt 0) { Round-Number (($sie / $total) * 100) } else { 0.0 }
    }
  }
)

$familyToMarkets = [ordered]@{}
foreach ($family in $familyOrder) {
  $familyToMarkets.Add($family, @())
}
foreach ($market in $dddMarketConfig.Keys) {
  $family = $dddMarketConfig[$market].family
  $familyToMarkets[$family] = @($familyToMarkets[$family] + $market)
}
$familyToMarkets['Totales'] = @($dddMarketConfig.Keys)

$summary = [ordered]@{}
foreach ($family in $familyOrder) {
  $budgetFamily = if ($budgetFamilies.Contains($family)) { $budgetFamilies[$family] } else { $null }
  $stockFamily = if ($stockFamilies.Contains($family)) { $stockFamilies[$family] } else { $null }
  $channelFamily = if ($channelFamilies.Contains($family)) { $channelFamilies[$family] } else { $null }
  $rxFamily = if ($rxFamiliesOut.Contains($family)) { $rxFamiliesOut[$family] } else { $null }
  $shareFamily = if ($dashboardShareOut.Contains($family)) { $dashboardShareOut[$family] } else { $null }

  $latestBudgetActual = 0
  $latestBudgetTarget = 0
  $ytdActual2026 = 0
  $ytdBudget2026 = 0
  if ($budgetFamily) {
    $latestBudgetActual = [math]::Round(($budgetFamily.actual[$budgetMonths.IndexOf($budgetCut)]), 0)
    $latestBudgetTarget = [math]::Round(($budgetFamily.budget[$budgetMonths.IndexOf($budgetCut)]), 0)
    $ytdActual2026 = Get-YtdSum -Months $budgetMonths -Values $budgetFamily.actual -Year 2026 -CutMonth $budgetCut
    $ytdBudget2026 = Get-YtdSum -Months $budgetMonths -Values $budgetFamily.budget -Year 2026 -CutMonth $budgetCut
  }

  $latestStockDays = 0
  if ($stockFamily) {
    $latestStockDays = [math]::Round(($stockFamily.days[$stockMonths.IndexOf($stockCut)]), 0)
  }

  $latestRx = 0
  if ($rxFamily -and $rxFamily.latestMonth) {
    $latestRx = [math]::Round(($rxFamily.prescriptions[$rxMonths.IndexOf($rxFamily.latestMonth)]), 0)
  }

  $latestShare = 0.0
  if ($shareFamily -and $shareFamily.Count -gt 0) {
    $latestShare = $shareFamily[-1].share
  }

  $summary.Add($family, [ordered]@{
    ytdActual2026 = $ytdActual2026
    ytdBudget2026 = $ytdBudget2026
    compliance2026 = if ($ytdBudget2026 -gt 0) { Round-Number (($ytdActual2026 / $ytdBudget2026) * 100) } else { 0.0 }
    latestMonth = $budgetCut
    latestActual = $latestBudgetActual
    latestBudget = $latestBudgetTarget
    latestStockDays = $latestStockDays
    convenioPct = if ($channelFamily) { $channelFamily.convenioPct } else { 0.0 }
    latestRx = $latestRx
    latestShare = $latestShare
    hasDdd = ($familyToMarkets[$family].Count -gt 0)
  })
}

$data = [ordered]@{
  meta = [ordered]@{
    generatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm')
    sourceDir = $SourceDir
    budgetCut = $budgetCut
    stockCut = $stockCut
    rxCut = Get-LastNonZeroMonth -Months $rxMonths -Values $rxFamiliesOut['Totales'].prescriptions
    dddCut = $dddMonths[-1]
  }
  families = $familyOrder
  familyToMarkets = $familyToMarkets
  summary = $summary
  budget = [ordered]@{
    months = $budgetMonths
    families = $budgetFamilies
    topProducts = $budgetProducts
  }
  stock = [ordered]@{
    months = $stockMonths
    families = $stockFamilies
    topProducts = $stockProducts
  }
  channel = [ordered]@{
    families = $channelFamilies
  }
  osComparison = [ordered]@{
    families = $osFamilies
  }
  prescriptions = [ordered]@{
    months = $rxMonths
    families = $rxFamiliesOut
  }
  marketShare = [ordered]@{
    months = $dddMonths
    families = $dashboardShareOut
  }
  ddd = [ordered]@{
    months = $dddMonths
    markets = $dddMarketsOut
  }
}

$json = $data | ConvertTo-Json -Depth 40 -Compress
$content = "window.OTC_DATA = $json;"
Set-Content -LiteralPath $OutputPath -Value $content -Encoding UTF8
Write-Output "OTC data generated: $OutputPath"
