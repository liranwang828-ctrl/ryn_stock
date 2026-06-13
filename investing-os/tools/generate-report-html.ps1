param(
  [string]$ReportId = 'RPT-2026-06-05-MAJOR-DRAWDOWN'
)

$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
$ReportsIndexPath = Join-Path $Root 'system\traceability\reports-index.json'
$ReportsDir = Join-Path $Root 'dashboards\reports'

if (!(Test-Path -LiteralPath $ReportsDir)) {
  New-Item -ItemType Directory -Path $ReportsDir | Out-Null
}

function Escape-Html([string]$Text) {
  if ($null -eq $Text) { return '' }
  return $Text.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;')
}

function Convert-InlineMarkdown([string]$Text) {
  $Escaped = Escape-Html $Text
  $Escaped = [regex]::Replace($Escaped, '`([^`]+)`', '<code>$1</code>')
  $Escaped = [regex]::Replace($Escaped, '\*\*([^*]+)\*\*', '<strong>$1</strong>')
  return $Escaped
}

function Convert-Table($Rows) {
  if ($Rows.Count -lt 2) { return ($Rows | ForEach-Object { "<p>$(Convert-InlineMarkdown $_)</p>" }) -join "`n" }
  $Header = $Rows[0].Trim('|').Split('|') | ForEach-Object { $_.Trim() }
  $Body = $Rows | Select-Object -Skip 2
  $Html = "<table><thead><tr>"
  foreach ($Cell in $Header) { $Html += "<th>$(Convert-InlineMarkdown $Cell)</th>" }
  $Html += "</tr></thead><tbody>"
  foreach ($Row in $Body) {
    if ($Row.Trim() -eq '') { continue }
    $Cells = $Row.Trim('|').Split('|') | ForEach-Object { $_.Trim() }
    $Html += "<tr>"
    foreach ($Cell in $Cells) { $Html += "<td>$(Convert-InlineMarkdown $Cell)</td>" }
    $Html += "</tr>"
  }
  $Html += "</tbody></table>"
  return $Html
}

function Convert-MarkdownToHtml([string]$Markdown) {
  $Lines = $Markdown -split "`r?`n"
  $Out = New-Object System.Collections.Generic.List[string]
  $InCode = $false
  $Code = New-Object System.Collections.Generic.List[string]
  $ListOpen = $false
  $Table = New-Object System.Collections.Generic.List[string]

  function Flush-List {
    if ($script:ListOpen) {
      $script:Out.Add('</ul>')
      $script:ListOpen = $false
    }
  }

  function Flush-Table {
    if ($script:Table.Count -gt 0) {
      $script:Out.Add((Convert-Table $script:Table))
      $script:Table.Clear()
    }
  }

  foreach ($Line in $Lines) {
    if ($Line -match '^\s*```') {
      if ($InCode) {
        $Out.Add("<pre><code>$(Escape-Html (($Code -join "`n")))</code></pre>")
        $Code.Clear()
        $InCode = $false
      } else {
        Flush-List
        Flush-Table
        $InCode = $true
      }
      continue
    }

    if ($InCode) {
      $Code.Add($Line)
      continue
    }

    if ($Line -match '^\s*\|.*\|\s*$') {
      Flush-List
      $Table.Add($Line)
      continue
    } else {
      Flush-Table
    }

    if ($Line -match '^(#{1,4})\s+(.+)$') {
      Flush-List
      $Level = [Math]::Min($Matches[1].Length, 4)
      $Text = Convert-InlineMarkdown $Matches[2]
      $Out.Add("<h$Level>$Text</h$Level>")
      continue
    }

    if ($Line -match '^\s*-\s+(.+)$') {
      if (!$ListOpen) {
        $Out.Add('<ul>')
        $ListOpen = $true
      }
      $Out.Add("<li>$(Convert-InlineMarkdown $Matches[1])</li>")
      continue
    }

    if ($Line.Trim() -eq '') {
      Flush-List
      continue
    }

    Flush-List
    $Out.Add("<p>$(Convert-InlineMarkdown $Line)</p>")
  }

  Flush-List
  Flush-Table
  return $Out -join "`n"
}

$Reports = Get-Content -Raw -Encoding UTF8 $ReportsIndexPath | ConvertFrom-Json
$Report = $Reports | Where-Object { $_.id -eq $ReportId } | Select-Object -First 1

if ($null -eq $Report) {
  throw "Report not found: $ReportId"
}

$SourcePath = Join-Path $Root $Report.path
if (!(Test-Path -LiteralPath $SourcePath)) {
  throw "Source markdown not found: $SourcePath"
}

$Slug = [IO.Path]::GetFileNameWithoutExtension($Report.path)
$OutputPath = Join-Path $ReportsDir "$Slug.html"
$Markdown = Get-Content -Raw -Encoding UTF8 $SourcePath
$Body = Convert-MarkdownToHtml $Markdown
$GeneratedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
$FragmentPath = Join-Path $Root "dashboards\report-fragments\$ReportId.zh.html"
$ReaderBody = $null
if (Test-Path -LiteralPath $FragmentPath) {
  $ReaderBody = Get-Content -Raw -Encoding UTF8 $FragmentPath
}
$TypeLabel = switch ($Report.type) {
  'post_market_review' { '&#30424;&#21518;&#22797;&#30424; / Post-Market Review' }
  'daily_report' { '&#27599;&#26085;&#25253;&#21578; / Daily Report' }
  'pre_market_report' { '&#30424;&#21069;&#35745;&#21010; / Pre-Market Plan' }
  'trade_review' { '&#20132;&#26131;&#22797;&#30424; / Trade Review' }
  'company_research' { '&#20844;&#21496;&#30740;&#31350; / Company Research' }
  'industry_research' { '&#34892;&#19994;&#30740;&#31350; / Industry Research' }
  'evidence_source' { '&#35777;&#25454;&#26469;&#28304; / Evidence Source' }
  default { "$($Report.type)" }
}
$StatusLabel = '&#29366;&#24577; / Status'
$GeneratedLabel = '&#29983;&#25104;&#26102;&#38388; / Generated'
$SourceLabel = '&#25171;&#24320;&#28304; Markdown / Source'
$BackLabel = '&#36820;&#22238; Dashboard / Back'

$Html = @"
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>$($Report.cn)</title>
  <style>
    body { margin: 0; background: #f4f6f8; color: #172033; font-family: Arial, "Microsoft YaHei", sans-serif; line-height: 1.58; }
    header { position: sticky; top: 0; background: #fff; border-bottom: 1px solid #d7dee8; padding: 14px 22px; z-index: 1; }
    main { max-width: 1080px; margin: 0 auto; padding: 22px; }
    article { background: #fff; border: 1px solid #d7dee8; border-radius: 8px; padding: 24px; }
    h1 { margin: 0 0 6px; font-size: 24px; }
    h2 { margin-top: 28px; padding-top: 14px; border-top: 1px solid #edf0f4; font-size: 20px; }
    h3 { margin-top: 22px; font-size: 16px; }
    p, li { font-size: 14px; }
    .meta { color: #667085; font-size: 13px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .chip { display: inline-flex; border: 1px solid #d7dee8; border-radius: 999px; padding: 2px 9px; background: #f9fafb; color: #475467; font-weight: 700; }
    .actions { margin-top: 8px; display: flex; gap: 10px; flex-wrap: wrap; }
    a { color: #175cd3; text-decoration: none; }
    a:hover { text-decoration: underline; }
    pre { overflow: auto; background: #101828; color: #f2f4f7; padding: 12px; border-radius: 7px; font-size: 12px; }
    code { background: #f2f4f7; border: 1px solid #e4e7ec; border-radius: 4px; padding: 1px 4px; font-family: Consolas, monospace; }
    pre code { background: transparent; border: 0; padding: 0; color: inherit; }
    table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13px; }
    th, td { border-bottom: 1px solid #e4e7ec; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #f9fafb; color: #475467; }
    ul { padding-left: 22px; }
    ol { padding-left: 22px; }
    .reader-summary { border: 1px solid #b2ddff; background: #f5fbff; border-radius: 8px; padding: 18px; margin-bottom: 18px; }
    details { margin-top: 18px; border: 1px solid #e4e7ec; border-radius: 8px; background: #fcfcfd; padding: 12px 16px; }
    summary { cursor: pointer; font-weight: 700; color: #175cd3; }
  </style>
</head>
<body>
  <header>
    <h1>$($Report.cn)</h1>
    <div class="meta">
      <span class="chip">$TypeLabel</span>
      <span class="chip">${StatusLabel}: $($Report.status)</span>
      <span class="chip">${GeneratedLabel}: $GeneratedAt</span>
    </div>
    <div class="actions">
      <a href="../../$($Report.path)">$SourceLabel</a>
      <a href="../growth-dashboard-draft.html">$BackLabel</a>
    </div>
  </header>
  <main>
    <article>
"@

if ($ReaderBody) {
  $Html += @"
$ReaderBody
<details>
  <summary>&#26597;&#30475;&#21407;&#22987; Markdown &#28210;&#26579;&#20869;&#23481; / Original Rendered Markdown</summary>
$Body
</details>
"@
} else {
  $Html += @"
$Body
"@
}

$Html += @"
    </article>
  </main>
</body>
</html>
"@

Set-Content -LiteralPath $OutputPath -Value $Html -Encoding UTF8
Write-Host "Generated report HTML: $OutputPath"
