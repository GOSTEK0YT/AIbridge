param([switch]$WaitForStudio)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $root "release\AI-Bridge-Cloud.rbxmx"
$target = Join-Path $env:LOCALAPPDATA "Roblox\Plugins\Script.rbxmx"
$status = Join-Path $root "release\plugin-install-status.txt"

$studio = Get-Process RobloxStudioBeta -ErrorAction SilentlyContinue
if ($studio -and -not $WaitForStudio) {
    throw "Close Roblox Studio before installing the plugin."
}
if ($studio) {
    $studio | Wait-Process
    Start-Sleep -Seconds 2
}

Copy-Item -LiteralPath $source -Destination $target -Force
$content = Get-Content -Raw -LiteralPath $target
if (-not $content.Contains("https://ai-bridge-cloud.onrender.com")) {
    throw "The installed plugin does not contain the cloud endpoint."
}
"installed $(Get-Date -Format o)" | Set-Content -LiteralPath $status -Encoding UTF8
