# Installs the "Three Cards Motion" project into CapCut for Windows.
# CapCut stores media as absolute paths, so after copying the project folder this
# script writes the real folder path into draft_content.json.
$ErrorActionPreference = 'Stop'
$project = 'Three Cards Motion'
$source = Join-Path $PSScriptRoot $project

try {
    if (-not (Test-Path -LiteralPath (Join-Path $source 'draft_content.json'))) {
        throw "The folder '$project' was not found next to this file. Extract the whole zip first (right-click > Extract All)."
    }
    if (Get-Process -Name 'CapCut' -ErrorAction SilentlyContinue) {
        Read-Host 'CapCut is open. Close CapCut, then press Enter'
    }

    $root = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft'
    if (Test-Path -LiteralPath $root) {
        Write-Host "CapCut projects folder: $root"
        $answer = Read-Host 'Press Enter to install here, or paste another folder (CapCut > Settings > Draft location)'
    } else {
        $answer = Read-Host 'Paste your CapCut projects folder (CapCut > Settings > Draft location)'
    }
    if ($answer) { $root = $answer.Trim().Trim('"') }
    if (-not $root -or -not (Test-Path -LiteralPath $root)) { throw "Folder not found: $root" }

    $target = Join-Path $root $project
    if (Test-Path -LiteralPath $target) { $target = "$target $(Get-Date -Format 'yyyy-MM-dd HH-mm-ss')" }
    Copy-Item -LiteralPath $source -Destination $target -Recurse

    $dir = (Resolve-Path -LiteralPath $target).ProviderPath -replace '\\', '/'
    $file = Join-Path $target 'draft_content.json'
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $json = [IO.File]::ReadAllText($file, $utf8).Replace('__PROJECT_DIR__', $dir)
    [IO.File]::WriteAllText($file, $json, $utf8)

    Write-Host ''
    Write-Host "Done. Open CapCut and click the project '$(Split-Path $target -Leaf)'." -ForegroundColor Green
} catch {
    Write-Host ''
    Write-Host "Install failed: $($_.Exception.Message)" -ForegroundColor Red
}
