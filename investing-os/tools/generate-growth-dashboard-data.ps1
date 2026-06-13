param()

$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
$OutFile = Join-Path $Root 'dashboards\assets\growth-dashboard-indexes.js'

$ReportsPath = Join-Path $Root 'system\traceability\reports-index.json'
$LessonsPath = Join-Path $Root 'system\traceability\lesson-index.json'
$FileLineagePath = Join-Path $Root 'system\traceability\file-lineage-index.json'
$CapabilityHistoryPath = Join-Path $Root 'system\traceability\capability-history.json'

$ReportsJson = Get-Content -Raw -Encoding UTF8 $ReportsPath
$LessonsJson = Get-Content -Raw -Encoding UTF8 $LessonsPath
$FileLineageJson = Get-Content -Raw -Encoding UTF8 $FileLineagePath
$CapabilityHistoryJson = Get-Content -Raw -Encoding UTF8 $CapabilityHistoryPath

$Reports = $ReportsJson | ConvertFrom-Json
$Lessons = $LessonsJson | ConvertFrom-Json
$CapabilityHistory = $CapabilityHistoryJson | ConvertFrom-Json

$Js = @"
window.GROWTH_DASHBOARD_INDEXES = {
  reports: $ReportsJson,
  lessons: $LessonsJson,
  fileLineage: $FileLineageJson,
  capabilityHistory: $CapabilityHistoryJson
};
"@
Set-Content -LiteralPath $OutFile -Value $Js -Encoding UTF8

Write-Host "Loaded reports: $($Reports.Count)"
Write-Host "Loaded lessons: $($Lessons.Count)"
Write-Host "Loaded capability records: $($CapabilityHistory.Count)"
Write-Host "Generated: $OutFile"
