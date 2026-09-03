<#
.SYNOPSIS
  Start the Barrin's ecosystem web services locally, bound to 0.0.0.0 so
  other devices on your Wi-Fi / LAN can reach them.

.DESCRIPTION
  Launches each service in its own PowerShell window (logs stream live;
  Ctrl+C in a window stops just that service). The correct cross-device
  URLs are injected as environment variables at launch - your committed
  .env files are NOT modified.

  Databases: the backend .env files point at the remote dev database on
  146.59.146.57, so no local Postgres is needed - but this machine must be
  able to reach that host:5432.

  Batch jobs (barrins_scripture, karn_tablets) are not services and are
  not started here.

.PARAMETER Ip
  The LAN IP other devices should use. Auto-detected from the active
  default-gateway adapter when omitted.

.PARAMETER Only
  Comma-separated subset to start: api, identity, tamiyo, tolaria, goblin.
  Default: all five. Example: -Only identity,goblin  (just the T12 pair).

.PARAMETER Install
  Run dependency installs first (uv sync for backends; npm install for
  frontends; build @barrins/goblin-guide before the goblin shell).

.PARAMETER EmailVerification
  Start barrins_identity with REQUIRE_EMAIL_VERIFICATION=true. With SMTP
  unset the 6-digit code is written to that window's log / logs\app.log,
  so you can exercise the real /verify-email screen.

.PARAMETER Stop
  Don't start anything - free the known ports by killing whatever listens
  on them (8000, 8001, 5173, 5174, 5175).

.PARAMETER List
  Print the plan (services, ports, URLs, injected env) and exit.

.EXAMPLE
  .\scripts\dev\start-local.ps1 -Install

.EXAMPLE
  .\scripts\dev\start-local.ps1 -Only identity,goblin -EmailVerification

.EXAMPLE
  .\scripts\dev\start-local.ps1 -Stop
#>
[CmdletBinding()]
param(
  [string]$Ip,
  [string[]]$Only,
  [switch]$Install,
  [switch]$EmailVerification,
  [switch]$Stop,
  [switch]$List
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

# --- ports -----------------------------------------------------------------
$ports = @{ api = 8000; identity = 8001; tamiyo = 5173; tolaria = 5174; goblin = 5175 }

# --- stop mode -----------------------------------------------------------------
if ($Stop) {
  foreach ($p in ($ports.Values | Sort-Object)) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { Write-Host ("port {0,-5} - nothing listening" -f $p); continue }
    foreach ($procId in ($conns.OwningProcess | Select-Object -Unique)) {
      try {
        $name = (Get-Process -Id $procId -ErrorAction Stop).ProcessName
        Stop-Process -Id $procId -Force
        Write-Host ("port {0,-5} - stopped {1} (pid {2})" -f $p, $name, $procId)
      } catch {
        Write-Warning ("port {0} - could not stop pid {1}: {2}" -f $p, $procId, $_.Exception.Message)
      }
    }
  }
  return
}

# --- resolve LAN IP ----------------------------------------------------------
function Get-LanIp {
  $cfg = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
    Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
    Select-Object -First 1
  if ($cfg -and $cfg.IPv4Address.IPAddress) { return $cfg.IPv4Address.IPAddress }
  $addr = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' } |
    Select-Object -First 1
  if ($addr) { return $addr.IPAddress }
  return $null
}

if (-not $Ip) { $Ip = Get-LanIp }
if (-not $Ip) { throw "Could not auto-detect a LAN IP. Pass one explicitly: -Ip 192.168.1.x" }

# --- service definitions ---------------------------------------------------
# The frontend->API URLs and the backend CORS allow-lists are all built from
# $Ip so a phone/laptop on the same Wi-Fi works. localhost is kept in the
# CORS lists so this machine's own browser still works too.
$apiOrigins      = '["http://{0}:{1}","http://{0}:{2}","http://localhost:{1}","http://localhost:{2}"]' -f $Ip, $ports.tamiyo, $ports.tolaria
# Every browser SPA authenticates directly against barrins_identity since the
# Phase 7 identity cutover - Goblin Guide and Tamiyo Scroll today, Tolaria News
# once Q-02 lands - so identity's CORS list spans all three frontend ports, not
# just goblin's.
$identityOrigins = '["http://{0}:{1}","http://{0}:{2}","http://{0}:{3}","http://localhost:{1}","http://localhost:{2}","http://localhost:{3}"]' -f $Ip, $ports.goblin, $ports.tamiyo, $ports.tolaria

$identityEnv = [ordered]@{
  ALLOWED_ORIGINS   = $identityOrigins
  FRONTEND_BASE_URL = 'http://{0}:{1}' -f $Ip, $ports.goblin
}
if ($EmailVerification) { $identityEnv['REQUIRE_EMAIL_VERIFICATION'] = 'true' }

if ($EmailVerification) {
  $identityNote = 'REQUIRE_EMAIL_VERIFICATION=true (code goes to this log)'
} else {
  $identityNote = 'REQUIRE_EMAIL_VERIFICATION from .env (currently false)'
}

$services = [ordered]@{
  api = @{
    Title = 'barrins_api :8000'
    Dir   = Join-Path $repoRoot 'apps\barrins_api'
    Kind  = 'backend'
    Port  = $ports.api
    Env   = [ordered]@{ ALLOWED_ORIGINS = $apiOrigins }
    Note  = 'needs the remote dev DB + migrations applied'
  }
  identity = @{
    Title = 'barrins_identity :8001'
    Dir   = Join-Path $repoRoot 'apps\barrins_identity'
    Kind  = 'backend'
    Port  = $ports.identity
    Env   = $identityEnv
    Note  = $identityNote
  }
  tamiyo = @{
    Title = 'tamiyo_scroll :5173'
    Dir   = Join-Path $repoRoot 'apps\tamiyo_scroll'
    Kind  = 'frontend'
    Port  = $ports.tamiyo
    Env   = [ordered]@{ VITE_API_BASE_URL = 'http://{0}:{1}' -f $Ip, $ports.api }
    Note  = 'talks to barrins_api'
  }
  tolaria = @{
    Title = 'tolaria_news :5174'
    Dir   = Join-Path $repoRoot 'apps\tolaria_news'
    Kind  = 'frontend'
    Port  = $ports.tolaria
    Env   = [ordered]@{ VITE_API_BASE_URL = 'http://{0}:{1}' -f $Ip, $ports.api }
    Note  = 'talks to barrins_api'
  }
  goblin = @{
    Title = 'goblin_guide :5175'
    Dir   = Join-Path $repoRoot 'apps\goblin_guide'
    Kind  = 'frontend'
    Port  = $ports.goblin
    Env   = [ordered]@{ VITE_IDENTITY_SERVICE_URL = 'http://{0}:{1}' -f $Ip, $ports.identity }
    Note  = 'talks to barrins_identity'
  }
}

if ($Only) {
  # accept both "-Only identity,goblin" (array) and "-Only identity,goblin"
  # passed as one string via -File
  $keys = $Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ }
} else {
  $keys = @($services.Keys)
}
foreach ($k in $keys) {
  if (-not $services.Contains($k)) { throw "Unknown service '$k'. Choose from: $($services.Keys -join ', ')" }
}

# --- plan -----------------------------------------------------------------
Write-Host ""
Write-Host "Bind IP : $Ip   (loopback also served)" -ForegroundColor Cyan
Write-Host "Repo    : $repoRoot" -ForegroundColor Cyan
Write-Host ""
foreach ($k in $keys) {
  $s = $services[$k]
  Write-Host ("  {0,-22} http://{1}:{2}    ({3})" -f $s.Title, $Ip, $s.Port, $s.Note)
  foreach ($e in $s.Env.GetEnumerator()) { Write-Host ("      {0}={1}" -f $e.Key, $e.Value) -ForegroundColor DarkGray }
}
Write-Host ""

if ($List) { return }

# --- installs (synchronous) ---------------------------------------------------
if ($Install) {
  Write-Host "Installing dependencies..." -ForegroundColor Yellow
  foreach ($k in $keys) {
    $s = $services[$k]
    Push-Location $s.Dir
    try {
      if ($s.Kind -eq 'backend') {
        uv sync --all-extras --dev
      } elseif ($k -eq 'goblin') {
        Push-Location (Join-Path $repoRoot 'libs\goblin_guide')
        npm install
        npm run build
        Pop-Location
        npm install
      } else {
        npm install
      }
    } finally { Pop-Location }
  }
  Write-Host ""
}

# --- launch -----------------------------------------------------------------
# Each service runs in its own window via -EncodedCommand: the child command
# (which embeds a JSON ALLOWED_ORIGINS with double quotes) is passed as
# base64 UTF-16LE so PowerShell's -Command quote-mangling can't touch it.
foreach ($k in $keys) {
  $s = $services[$k]
  $lines = New-Object System.Collections.Generic.List[string]
  $lines.Add("`$Host.UI.RawUI.WindowTitle = '$($s.Title)'")
  $lines.Add("Set-Location -LiteralPath '$($s.Dir)'")
  foreach ($e in $s.Env.GetEnumerator()) {
    $val = $e.Value -replace "'", "''"
    $lines.Add("`$env:$($e.Key) = '$val'")
  }
  if ($s.Kind -eq 'backend') {
    # uv picks the app's own .venv; drop an inherited VIRTUAL_ENV so it
    # doesn't warn about the mismatch on every start.
    $lines.Add('$env:VIRTUAL_ENV = $null')
    $lines.Add("uv run uvicorn app.main:app --host 0.0.0.0 --port $($s.Port) --reload")
  } else {
    $lines.Add("npm run dev -- --host 0.0.0.0 --port $($s.Port) --strictPort")
  }
  $child   = $lines -join "`n"
  $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($child))
  Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-EncodedCommand', $encoded) | Out-Null
  Write-Host ("started {0}" -f $s.Title) -ForegroundColor Green
  Start-Sleep -Milliseconds 400
}

Write-Host ""
Write-Host "URLs for other devices on your Wi-Fi:" -ForegroundColor Cyan
foreach ($k in $keys) {
  $s = $services[$k]
  Write-Host ("  {0,-16} http://{1}:{2}" -f $k, $Ip, $s.Port)
}
Write-Host ""
Write-Host "First launch: Windows Firewall will prompt to allow python/node -" -ForegroundColor Yellow
Write-Host "tick 'Private networks' or the LAN URLs stay unreachable." -ForegroundColor Yellow
Write-Host ("Health check: http://{0}:8001/health" -f $Ip)
Write-Host "Stop everything: .\scripts\dev\start-local.ps1 -Stop"
Write-Host ""
