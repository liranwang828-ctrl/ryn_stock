param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$resolved = Resolve-Path -LiteralPath $Path
$content = [System.IO.File]::ReadAllText($resolved, [System.Text.Encoding]::UTF8)
Write-Output $content
