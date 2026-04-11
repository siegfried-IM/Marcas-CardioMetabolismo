param(
  [string]$DddPath = 'C:\Users\camarinaro\Downloads\DDD LINEA MUJER.xlsx',
  [string]$PricePath = 'C:\Users\camarinaro\Downloads\PRECIO LINEA MUJER 10-04-26.xlsx',
  [string]$OutputPath = (Join-Path $PSScriptRoot 'price-ddd-overrides.js')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$monthNumMap = @{ 1='Jan'; 2='Feb'; 3='Mar'; 4='Apr'; 5='May'; 6='Jun'; 7='Jul'; 8='Aug'; 9='Sep'; 10='Oct'; 11='Nov'; 12='Dec' }
$familyOrder = @('ISIS FREE','ISIS','ISIS MINI','ISIS MINI 24','SIDERBLUT COMPLEX','SIDERBLUT','SIDERBLUT POLI','SIDERBLUT FOLICO','TRIP D3','TRIP +45','TRIP D3 PLUS','TRIP MAGNESIO','DELTROX NF','CALCIO BASE DUPOMAR','CALCIO BASE DUPOMAR D','CALCIO CITRATO DUPOMAR D3 200','CALCIO CITRATO DUPOMAR D3 400','CLIMATIX')

function T([object]$v){ if($null -eq $v){''} else { ([string]$v).Trim() } }
function N([object]$v){ if($null -eq $v){0.0} elseif($v -is [double] -or $v -is [single] -or $v -is [decimal] -or $v -is [int] -or $v -is [long]){ [double]$v } else { $t=(T $v); if(-not $t -or $t -eq '-'){0.0}else{ $t=$t.Replace('.','').Replace('%','').Replace(',','.'); $n=0.0; if([double]::TryParse($t,[Globalization.NumberStyles]::Any,[Globalization.CultureInfo]::InvariantCulture,[ref]$n)){ $n } else {0.0} } } }
function Month([object]$v){
  if($v -is [double] -or $v -is [single] -or $v -is [decimal] -or $v -is [int] -or $v -is [long]){
    try { $d=[datetime]::FromOADate([double]$v); return '{0} {1}' -f $monthNumMap[$d.Month], $d.Year } catch {}
  }
  $t=(T $v)
  if($t -match '^([A-Za-z]{3})-(\d{4})$'){
    $abbr=$matches[1].Substring(0,3).ToLower()
    $num=@{jan=1;feb=2;mar=3;apr=4;may=5;jun=6;jul=7;aug=8;sep=9;oct=10;nov=11;dec=12}[$abbr]
    if($num){ return '{0} {1}' -f $monthNumMap[$num], $matches[2] }
  }
  if($t -match '^([A-Za-z]{3}) (\d{4})$'){
    $abbr=$matches[1].Substring(0,3).ToLower()
    $num=@{jan=1;feb=2;mar=3;apr=4;may=5;jun=6;jul=7;aug=8;sep=9;oct=10;nov=11;dec=12}[$abbr]
    if($num){ return '{0} {1}' -f $monthNumMap[$num], $matches[2] }
  }
  return $t.Trim()
}
function MonthSort([string]$m){ if($m -match '^([A-Za-z]{3}) (\d{4})$'){ $map=@{Jan=1;Feb=2;Mar=3;Apr=4;May=5;Jun=6;Jul=7;Aug=8;Sep=9;Oct=10;Nov=11;Dec=12}; return ([int]$matches[2])*100 + $map[$matches[1]] } return 0 }
function Family([string]$candidate){
  $p = (T $candidate).ToUpper()
  if(-not $p){ return '' }
  if($p.Contains('ISIS FREE') -or $p -eq 'DROSPIRENONA'){ return 'ISIS FREE' }
  if($p.Contains('ISIS MINI 24')){ return 'ISIS MINI 24' }
  if($p.Contains('ISIS MINI')){ return 'ISIS MINI' }
  if($p.Contains('ISIS') -or $p.Contains('ETINILESTRADIOL')){ return 'ISIS' }
  if($p.Contains('SIDERBLUT FOLIC')){ return 'SIDERBLUT FOLICO' }
  if($p.Contains('SIDERBLUT POLI')){ return 'SIDERBLUT POLI' }
  if($p.Contains('SIDERBLUT COMPLEX')){ return 'SIDERBLUT COMPLEX' }
  if($p.Contains('SIDERBLUT')){ return 'SIDERBLUT' }
  if($p.Contains('TRIP D3 PLUS')){ return 'TRIP D3 PLUS' }
  if($p.Contains('TRIP +45')){ return 'TRIP +45' }
  if($p.Contains('TRIP MAGNESIO')){ return 'TRIP MAGNESIO' }
  if($p.Contains('TRIP D3') -or $p.Contains('TRIP')){ return 'TRIP D3' }
  if($p.Contains('DELTROX')){ return 'DELTROX NF' }
  if($p.Contains('CALCIO CITRATO') -and $p.Contains('400')){ return 'CALCIO CITRATO DUPOMAR D3 400' }
  if($p.Contains('CALCIO CITRATO')){ return 'CALCIO CITRATO DUPOMAR D3 200' }
  if($p.Contains('CALCIO BASE') -and ($p.Contains(' D ') -or $p.EndsWith(' D') -or $p.Contains(' D3'))){ if($p.Contains('400')){ return 'CALCIO CITRATO DUPOMAR D3 400' } if($p.Contains('200')){ return 'CALCIO CITRATO DUPOMAR D3 200' } return 'CALCIO BASE DUPOMAR D' }
  if($p.Contains('CALCIO BASE')){ return 'CALCIO BASE DUPOMAR' }
  if($p.Contains('CLIMATIX')){ return 'CLIMATIX' }
  return ''
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
  $wb = $excel.Workbooks.Open($DddPath)
  $ws = $wb.Worksheets.Item(1)
  $ddd = $ws.UsedRange.Value2
  $wb.Close($false)

  $wb = $excel.Workbooks.Open($PricePath)
  $ws = $wb.Worksheets.Item(1)
  $price = $ws.UsedRange.Value2
  $wb.Close($false)
}
finally {
  $excel.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}

$dddMonths = New-Object 'System.Collections.Generic.HashSet[string]'
$dddMarkets = @{}
for($r=2; $r -le $ddd.GetLength(0); $r++){
  $family = Family (T $ddd[$r,2])
  if(-not $family){ continue }
  $month = Month $ddd[$r,5]
  $region = T $ddd[$r,1]
  $product = T $ddd[$r,8]
  $units = N $ddd[$r,9]
  if(-not $month -or -not $region -or -not $product -or $units -le 0){ continue }
  $dddMonths.Add($month) | Out-Null
  if(-not $dddMarkets.Contains($family)){ $dddMarkets[$family] = @{ family=$family; latestMonth=''; productsByMonth=@{}; regionsByMonth=@{} } }
  if(-not $dddMarkets[$family].productsByMonth.Contains($month)){ $dddMarkets[$family].productsByMonth[$month] = @() }
  if(-not $dddMarkets[$family].regionsByMonth.Contains($month)){ $dddMarkets[$family].regionsByMonth[$month] = @() }
  $dddMarkets[$family].productsByMonth[$month] += [ordered]@{ product=$product; units=[math]::Round($units,0); share=0; isSie=($product.ToUpper().Contains($family)) }
  $dddMarkets[$family].regionsByMonth[$month] += [ordered]@{ name=$region; rr='__NAC__'; total=[math]::Round($units,0); sie=0; share=0 }
}

$dddMonthsSorted = @($dddMonths | Sort-Object { MonthSort $_ })
foreach($fam in @($dddMarkets.Keys)){
  foreach($m in $dddMonthsSorted){
    if(-not $dddMarkets[$fam].productsByMonth.ContainsKey($m)){ $dddMarkets[$fam].productsByMonth[$m]=@() }
    if(-not $dddMarkets[$fam].regionsByMonth.ContainsKey($m)){ $dddMarkets[$fam].regionsByMonth[$m]=@() }
  }
  $dddMarkets[$fam].latestMonth = ($dddMonthsSorted | Select-Object -Last 1)
}

$precios = [ordered]@{}
$prevLabel = (T $price[1,13])
$currLabel = (T $price[1,14])
for($r=2; $r -le $price.GetLength(0); $r++){
  $fam = Family (T $price[$r,3])
  $prod = T $price[$r,3]
  $pres = T $price[$r,4]
  $lab = T $price[$r,7]
  if(-not $fam -or -not $pres){ continue }
  if(-not $precios.Contains($fam)){ $precios[$fam] = [ordered]@{} }
  if(-not $precios[$fam].Contains($pres)){ $precios[$fam].Add($pres, @()) }
  $precios[$fam][$pres] += [ordered]@{
    lab = $lab
    prod = $prod
    is_sie = $lab.ToUpper().Contains('SIEGFRIED')
    pvp_dic25 = [math]::Round((N $price[$r,13]),2)
    pvp_feb26 = [math]::Round((N $price[$r,14]),2)
    var = if((N $price[$r,15]) -ne 0){ (N $price[$r,15]) / 100 } else { 0.0 }
  }
}

$payload = [ordered]@{
  ddd = [ordered]@{
    months = $dddMonthsSorted
    markets = $dddMarkets
  }
  precios = $precios
  priceMeta = [ordered]@{
    prevLabel = $prevLabel
    currLabel = $currLabel
  }
}

$json = $payload | ConvertTo-Json -Depth 20 -Compress
Set-Content -LiteralPath $OutputPath -Value ("window.MUJER_EXTRA_OVERRIDE = $json;") -Encoding UTF8
Write-Output "Extra overrides generated: $OutputPath"
