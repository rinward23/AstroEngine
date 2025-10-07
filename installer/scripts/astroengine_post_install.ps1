[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot,

    [Parameter(Mandatory = $true)]
    [ValidateSet('Online', 'Offline')]
    [string]$Mode,

    [Parameter()]
    [ValidateSet('PerUser', 'AllUsers')]
    [string]$Scope = 'PerUser',

    [Parameter()]
    [string]$SwissSource = '',

    [Parameter()]
    [string]$ManifestPath = '',

    [switch]$InstallPython,

    [switch]$ConfigureFirewall,

    [Parameter()]
    [string]$LogPath = ''
)

$ErrorActionPreference = 'Stop'

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = 'INFO'
    )
    $timestamp = (Get-Date).ToString('s')
    $line = "[$timestamp] [$Level] $Message"
    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $line -Encoding UTF8
    }
    Write-Output $line
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Resolve-Manifest {
    param([string]$Path)
    if (-not $Path) {
        $Path = Join-Path $InstallRoot 'installer\manifests\online_python.json'
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Manifest not found at $Path"
    }
    $json = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $json.python.sha256) {
        throw "Manifest $Path is missing a sha256 value for the Python runtime. Update the manifest with the verified checksum."
    }
    return $json
}

function Test-FileHash {
    param(
        [string]$Path,
        [string]$Expected,
        [string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found at $Path"
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($hash -ne $Expected.ToLowerInvariant()) {
        throw "$Label checksum mismatch. Expected $Expected but received $hash."
    }
}

function Get-PythonPayload {
    $manifest = Resolve-Manifest -Path $ManifestPath
    if ($Mode -eq 'Online') {
        $downloadRoot = Join-Path $InstallRoot 'installer\cache'
        Ensure-Directory -Path $downloadRoot
        $destination = Join-Path $downloadRoot (Split-Path -Leaf $manifest.python.url)
        Write-Log "Downloading Python runtime from $($manifest.python.url)"
        Invoke-WebRequest -Uri $manifest.python.url -OutFile $destination -UseBasicParsing
        Test-FileHash -Path $destination -Expected $manifest.python.sha256 -Label 'Python runtime download'
        return @{ Path = $destination; Manifest = $manifest }
    }

    $offlineRoot = Join-Path $InstallRoot 'installer\offline'
    if (-not (Test-Path -LiteralPath $offlineRoot)) {
        throw "Offline payload directory missing at $offlineRoot"
    }
    $offlinePath = Join-Path $offlineRoot (Split-Path -Leaf $manifest.python.url)
    if (-not (Test-Path -LiteralPath $offlinePath)) {
        throw "Offline payload expected at $offlinePath but was not found"
    }
    Test-FileHash -Path $offlinePath -Expected $manifest.python.sha256 -Label 'Offline Python runtime'

    if ($manifest.wheels -and $manifest.wheels.Count -gt 0) {
        foreach ($wheel in $manifest.wheels) {
            if (-not $wheel.sha256) {
                throw "Wheel manifest entry for $($wheel.name) is missing a sha256 field."
            }
            $wheelPath = Join-Path $offlineRoot $wheel.name
            Test-FileHash -Path $wheelPath -Expected $wheel.sha256 -Label "Wheel $($wheel.name)"
        }
    }

    return @{ Path = $offlinePath; Manifest = $manifest }
}

function Expand-PythonRuntime {
    param([string]$ZipPath)
    $runtimeRoot = Join-Path $InstallRoot 'runtime'
    $target = Join-Path $runtimeRoot 'python311'
    Ensure-Directory -Path $runtimeRoot
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
    Ensure-Directory -Path $target
    Write-Log "Expanding Python runtime to $target"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $target)
    $pythonExe = Join-Path $target 'python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        throw "Python executable not found after extraction at $pythonExe"
    }
    return $pythonExe
}

function Invoke-Process {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [hashtable]$Env = @{}
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $escaped = foreach ($arg in $Arguments) {
        if ($arg -match '\s') {
            [System.Management.Automation.Language.CodeGeneration]::QuoteArgument($arg)
        } else {
            $arg
        }
    }
    $psi.Arguments = [string]::Join(' ', $escaped)
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($key in $Env.Keys) {
        $psi.Environment[$key] = $Env[$key]
    }
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    $process.Start() | Out-Null
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($stdout) {
        $stdout.TrimEnd().Split([Environment]::NewLine) | ForEach-Object { Write-Log $_ 'STDOUT' }
    }
    if ($stderr) {
        $stderr.TrimEnd().Split([Environment]::NewLine) | ForEach-Object { Write-Log $_ 'STDERR' }
    }
    if ($process.ExitCode -ne 0) {
        throw "Command '$FilePath $($psi.Arguments)' exited with code $($process.ExitCode)"
    }
}

function Initialize-Venv {
    param([string]$PythonExe)
    $venvRoot = Join-Path $InstallRoot 'env'
    if (Test-Path -LiteralPath $venvRoot) {
        Remove-Item -LiteralPath $venvRoot -Recurse -Force
    }
    Write-Log "Creating virtual environment at $venvRoot"
    Invoke-Process -FilePath $PythonExe -Arguments @('-m', 'venv', $venvRoot) -WorkingDirectory $InstallRoot
    $pip = Join-Path $venvRoot 'Scripts\pip.exe'
    if (-not (Test-Path -LiteralPath $pip)) {
        throw "pip was not installed in the virtual environment. Ensure ensurepip is available in the Python runtime."
    }
    return $venvRoot
}

function Install-Dependencies {
    param([string]$VenvRoot)
    $pip = Join-Path $VenvRoot 'Scripts\pip.exe'
    $requirements = Join-Path $InstallRoot 'requirements.lock\py311.txt'
    if (-not (Test-Path -LiteralPath $requirements)) {
        throw "Requirements lock file missing at $requirements"
    }
    Write-Log "Installing dependencies from $requirements"
    $env = @{ 'PIP_NO_INPUT' = '1' }
    $args = @('-m', 'pip', 'install', '--upgrade', 'pip')
    Invoke-Process -FilePath (Join-Path $VenvRoot 'Scripts\python.exe') -Arguments $args -WorkingDirectory $InstallRoot -Env $env
    $installArgs = @('-m', 'pip', 'install', '--require-hashes', '-r', $requirements)
    if ($Mode -eq 'Offline') {
        $offlineDir = Join-Path $InstallRoot 'installer\offline'
        $installArgs = @('-m', 'pip', 'install', '--no-index', '--find-links', $offlineDir, '--require-hashes', '-r', $requirements)
    }
    Invoke-Process -FilePath (Join-Path $VenvRoot 'Scripts\python.exe') -Arguments $installArgs -WorkingDirectory $InstallRoot -Env $env
}

function Initialize-Database {
    param([string]$VenvRoot)
    $dbDir = Join-Path $InstallRoot 'var'
    Ensure-Directory -Path $dbDir
    $env = @{ 'ASTROENGINE_DB_PATH' = (Join-Path $dbDir 'dev.db') }
    $alembicIni = Join-Path $InstallRoot 'alembic.ini'
    Write-Log "Running Alembic migrations"
    Invoke-Process -FilePath (Join-Path $VenvRoot 'Scripts\python.exe') -Arguments @('-m', 'alembic', '-c', $alembicIni, 'upgrade', 'head') -WorkingDirectory $InstallRoot -Env $env
}

function Write-EnvironmentFiles {
    $envPath = Join-Path $InstallRoot '.env'
    if (-not (Test-Path -LiteralPath $envPath)) {
        Write-Log "Creating default .env"
        $home = (Get-Item -LiteralPath $InstallRoot).FullName
        @(
            "ASTROENGINE_HOME=$home",
            'ASTROENGINE_API_HOST=127.0.0.1',
            'ASTROENGINE_API_PORT=8000',
            'ASTROENGINE_UI_HOST=127.0.0.1',
            'ASTROENGINE_UI_PORT=8501',
            'ASTROENGINE_DB_PATH=${ASTROENGINE_HOME}\var\dev.db'
        ) | Set-Content -LiteralPath $envPath -Encoding UTF8
    }
    $configDir = Join-Path $env:APPDATA 'AstroEngine'
    Ensure-Directory -Path $configDir
    $configPath = Join-Path $configDir 'config.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        $config = @{
            runtime = @{ python = 'runtime\\python311'; venv = 'env' }
            logging = @{ level = 'INFO' }
            scope = $Scope
            mode = $Mode
        } | ConvertTo-Json -Depth 4
        Write-Log "Writing config.json to $configPath"
        $config | Set-Content -LiteralPath $configPath -Encoding UTF8
    }
}

function Initialize-PortConfiguration {
    $configDir = Join-Path $InstallRoot 'config'
    Ensure-Directory -Path $configDir
    $portsPath = Join-Path $configDir 'ports.json'
    if (-not (Test-Path -LiteralPath $portsPath)) {
        $ports = @{ api = 8000; ui = 8501 } | ConvertTo-Json -Depth 2
        Write-Log "Seeding default ports configuration at $portsPath"
        $ports | Set-Content -LiteralPath $portsPath -Encoding UTF8
    }
}

function Copy-SwissEphemeris {
    if (-not $SwissSource) {
        Write-Log 'Swiss Ephemeris import skipped.'
        return
    }
    if (-not (Test-Path -LiteralPath $SwissSource)) {
        throw "Swiss Ephemeris source $SwissSource does not exist"
    }
    $destination = Join-Path $InstallRoot 'data\swiss'
    Ensure-Directory -Path $destination
    Write-Log "Copying Swiss Ephemeris data from $SwissSource"
    Get-ChildItem -Path (Join-Path $SwissSource '*') -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Recurse -Force
    }
}

function Test-Health {
    param([string]$VenvRoot)
    $python = Join-Path $VenvRoot 'Scripts\python.exe'
    $apiArgs = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000')
    Write-Log 'Running post-install API health check'
    $process = Start-Process -FilePath $python -ArgumentList $apiArgs -WorkingDirectory $InstallRoot -WindowStyle Hidden -PassThru
    try {
        $deadline = (Get-Date).AddSeconds(60)
        $healthy = $false
        while ((Get-Date) -lt $deadline) {
            try {
                $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 5
                if ($response.StatusCode -eq 200 -and $response.Content -match 'ok') {
                    $healthy = $true
                    break
                }
            } catch {
                Start-Sleep -Seconds 2
            }
        }
        if (-not $healthy) {
            throw 'API health check failed. Review logs in var\\logs or rerun installer in repair mode.'
        }
    }
    finally {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
}

function Configure-FirewallRules {
    if (-not $ConfigureFirewall) {
        return
    }
    if (-not (Get-Command -Name 'New-NetFirewallRule' -ErrorAction SilentlyContinue)) {
        Write-Log 'Firewall configuration skipped: New-NetFirewallRule cmdlet unavailable.' 'WARN'
        return
    }
    Write-Log 'Adding Windows Defender Firewall rules for AstroEngine ports'
    foreach ($port in @(8000, 8501)) {
        $name = "AstroEngine_$port"
        try {
            New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Program (Join-Path $InstallRoot 'env\Scripts\python.exe') -ErrorAction Stop | Out-Null
        } catch {
            Write-Log "Failed to create firewall rule for port $port: $($_.Exception.Message)" 'WARN'
        }
    }
}

if (-not $LogPath) {
    $LogPath = Join-Path $InstallRoot 'logs\install\post_install.log'
}
Ensure-Directory -Path (Split-Path -Path $LogPath -Parent)
$script:LogFile = $LogPath

Write-Log "Starting AstroEngine post-install sequence (Mode=$Mode, Scope=$Scope, InstallPython=$InstallPython)"
try {
    $payload = Get-PythonPayload
    $pythonExe = Expand-PythonRuntime -ZipPath $payload.Path
    $venvRoot = Initialize-Venv -PythonExe $pythonExe
    Install-Dependencies -VenvRoot $venvRoot
    Copy-SwissEphemeris
    Initialize-Database -VenvRoot $venvRoot
    Write-EnvironmentFiles
    Initialize-PortConfiguration
    Configure-FirewallRules
    Test-Health -VenvRoot $venvRoot
    Write-Log 'Post-install tasks completed successfully.'
} catch {
    Write-Log $_.Exception.Message 'ERROR'
    throw
}
