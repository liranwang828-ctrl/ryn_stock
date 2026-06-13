param(
  [int]$SoftLimit = 300,
  [int]$HardLimit = 500
)

$Root = Resolve-Path (Join-Path $PSScriptRoot '..')

$Paths = @(
  'cognition',
  'decision',
  'execution',
  'evolution',
  'system',
  'templates'
)

$Files = foreach ($Path in $Paths) {
  $Full = Join-Path $Root $Path
  if (Test-Path -LiteralPath $Full) {
    Get-ChildItem -LiteralPath $Full -Recurse -File -Filter '*.md'
  }
}

$Rows = foreach ($File in $Files) {
  $Lines = (Get-Content -LiteralPath $File.FullName | Measure-Object -Line).Lines
  $Status = if ($Lines -ge $HardLimit) {
    'hard_limit'
  } elseif ($Lines -ge $SoftLimit) {
    'soft_limit'
  } else {
    'ok'
  }

  [pscustomobject]@{
    status = $Status
    lines = $Lines
    file = $File.FullName.Replace($Root.Path + [IO.Path]::DirectorySeparatorChar, '')
  }
}

$Rows | Sort-Object @{Expression = { $_.status -eq 'ok' }}, @{Expression = 'lines'; Descending = $true} | Format-Table -AutoSize

if ($Rows.status -contains 'hard_limit') {
  exit 2
}

if ($Rows.status -contains 'soft_limit') {
  exit 1
}
