<#
.SYNOPSIS
  Start the Barrin's ecosystem web services locally, bound to 0.0.0.0 so
  other devices on your Wi-Fi / LAN can reach them.

.DESCRIPTION
  Launches each service in its own PowerShell window (logs stream live;
  Ctrl+C in a window stops just that service). The correct cross-device
  URLs are injected as environment variables at launch - your committed
  .env files are NOT modified.

  Auth caveat: the browser SPAs are pointed at barrins_identity on
  http://localhost:8001, not the LAN IP, because identity's refresh cookie
  is `Secure` and browsers only keep a `Secure` cookie over plain http for
  localhost. This keeps reload/auto-login + cross-app SSO working on THIS
  machine; logging in from another device on the Wi-Fi does not work. The
  tracker itself (barrins_api, Bearer-token, no cookie) is still reachable
  cross-device.

  When 'api' is started it also mints/rotates a local barrins_identity
  service account (sa_local_dev_directory) and injects its credentials so
  the Teams UI shows real member names instead of "Unknown member". See
  scripts/dev/README.md.

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

# The browser SPAs must reach barrins_identity on a *secure context* origin,
# not the bare LAN IP. Cookie mode (ADR-18) keeps the refresh token in an
# HttpOnly cookie that identity always sets `Secure` (core/cookies.py). A
# browser only stores a `Secure` cookie over plain http:// for localhost /
# 127.0.0.1 - over http://<lan-ip>:8001 it silently drops it, so a reload
# never restores the session and the two SPAs never share one. Pointing both
# frontends at http://localhost:<identity port> keeps auto-login + cross-app
# SSO working on this machine. Trade-off: another device on the Wi-Fi can't
# authenticate (its "localhost" is itself) - unavoidable while the cookie is
# hard-`Secure` over plain HTTP. barrins_api still uses the LAN IP: it takes a
# Bearer token, no cookie, so cross-device tracker use is unaffected.
$identityUrlForBrowser = 'http://localhost:{0}' -f $ports.identity

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
    Env   = [ordered]@{
      VITE_API_BASE_URL         = 'http://{0}:{1}' -f $Ip, $ports.api
      VITE_IDENTITY_SERVICE_URL = $identityUrlForBrowser
    }
    Note  = 'barrins_api (LAN IP) + barrins_identity (localhost, see note above)'
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
    Env   = [ordered]@{ VITE_IDENTITY_SERVICE_URL = $identityUrlForBrowser }
    Note  = 'talks to barrins_identity (localhost, see note above)'
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

# --- barrins_api's identity service account (synchronous) --------------------
# barrins_api resolves team-roster / deck-owner display names by calling
# barrins_identity's POST /api/v1/users/lookup, which needs a service-account
# token. Mint (or rotate) a stable local dev account straight in identity's DB
# and inject its credentials into the api window - otherwise every name in the
# Teams UI renders as "Unknown member". Best-effort: if identity's DB is
# unreachable the api still starts, just with the directory disabled.
if ($keys -contains 'api') {
  Write-Host "Provisioning barrins_api's identity service account..." -ForegroundColor Yellow
  $saArgs = @(
    'run', 'python', 'scripts/create_service_account.py',
    '--client-id', 'sa_local_dev_directory',
    '--description', 'barrins_api user-directory lookups (local dev)'
  )
  $saErr = [System.IO.Path]::GetTempFileName()
  $prevVenv = $env:VIRTUAL_ENV
  $prevEap = $ErrorActionPreference
  Push-Location (Join-Path $repoRoot 'apps\barrins_identity')
  try {
    # uv picks the app's own .venv; drop an inherited VIRTUAL_ENV so it does
    # not print a mismatch warning. Keep stderr out of the success stream and
    # off 'Stop' - in PS 5.1 a merged native-stderr line becomes a fatal
    # NativeCommandError, and uv is chatty on stderr even when it succeeds.
    $env:VIRTUAL_ENV = $null
    $ErrorActionPreference = 'Continue'
    $saOut = & uv @saArgs 2>$saErr
    $saExit = $LASTEXITCODE
  } finally {
    Pop-Location
    $env:VIRTUAL_ENV = $prevVenv
    $ErrorActionPreference = $prevEap
  }

  $clientId     = ($saOut | Select-String -Pattern '^CLIENT_ID=(.+)$'     | Select-Object -First 1).Matches.Groups[1].Value
  $clientSecret = ($saOut | Select-String -Pattern '^CLIENT_SECRET=(.+)$' | Select-Object -First 1).Matches.Groups[1].Value

  if ($saExit -eq 0 -and $clientId -and $clientSecret) {
    $services.api.Env['IDENTITY_SERVICE_URL']           = $identityUrlForBrowser
    $services.api.Env['IDENTITY_SERVICE_CLIENT_ID']     = $clientId
    $services.api.Env['IDENTITY_SERVICE_CLIENT_SECRET'] = $clientSecret
    Write-Host ("  ok - IDENTITY_SERVICE_CLIENT_ID={0} (secret injected, not shown)" -f $clientId) -ForegroundColor Green
  } else {
    Write-Warning "could not provision the identity service account - Teams names will show 'Unknown member'."
    $saDetail = (Get-Content -LiteralPath $saErr -Raw -ErrorAction SilentlyContinue)
    if ($saDetail) { Write-Warning ("detail: " + $saDetail.Trim()) }
    Write-Warning "fix: cd apps\barrins_identity; uv run python scripts/create_service_account.py --client-id sa_local_dev_directory"
  }
  Remove-Item -LiteralPath $saErr -Force -ErrorAction SilentlyContinue
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
