<#
.SYNOPSIS
    Stage 1 Probe-Only Guest Containment Audit Script (Hardened)
    PROBE-ONLY. DOES NOT LAUNCH MT5 OR EXECUTE HARNESSES.

.DESCRIPTION
    Runs inside the disposable Windows Sandbox instance to inspect IPv4 and IPv6
    network configuration, route tables, interface status, and active socket reachability.
    Explicitly surfaces any collection errors (no SilentlyContinue hiding failures).
    Binds output to a host-provided cryptographic session nonce and exports structured
    JSON telemetry to the mapped external results folder for independent host validation.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$NonceFilePath = "C:\SandboxStaging\session_nonce.txt",

    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "C:\SandboxResults\guest_containment_evidence.json"
)

$ErrorActionPreference = "Stop"

$startTimeUtc = [DateTime]::UtcNow.ToString("o")

# 1. Read Host Session Nonce
$sessionNonce = "MISSING_NONCE"
if (Test-Path $NonceFilePath) {
    $sessionNonce = (Get-Content $NonceFilePath -Raw).Trim()
}

# 2. Capture Guest Identity & Environment
$guestIdentity = @{
    ComputerName = $env:COMPUTERNAME
    UserName     = $env:USERNAME
    OSVersion    = [System.Environment]::OSVersion.ToString()
    Is64BitOS    = [System.Environment]::Is64BitOperatingSystem
    TimestampUtc = $startTimeUtc
    SessionNonce = $sessionNonce
}

# 3. Comprehensive Network Interface Audit (IPv4 and IPv6)
$adapterCollectionSuccess = $false
$adapterCollectionError = $null
$interfaces = @()
try {
    $netAdapters = Get-NetAdapter -ErrorAction Stop
    $adapterCollectionSuccess = $true
    if ($netAdapters) {
        foreach ($adapter in $netAdapters) {
            $interfaces += @{
                Name          = [string]$adapter.Name
                InterfaceDesc = [string]$adapter.InterfaceDescription
                Status        = [string]$adapter.Status
                LinkSpeed     = [string]$adapter.LinkSpeed
                MacAddress    = [string]$adapter.MacAddress
            }
        }
    }
} catch {
    $adapterCollectionSuccess = $false
    $adapterCollectionError = $_.Exception.Message
}

$ipCollectionSuccess = $false
$ipCollectionError = $null
$ipConfiguration = @()
try {
    $netIPConfigs = Get-NetIPConfiguration -ErrorAction Stop
    $ipCollectionSuccess = $true
    if ($netIPConfigs) {
        foreach ($cfg in $netIPConfigs) {
            $ipConfiguration += @{
                InterfaceAlias = [string]$cfg.InterfaceAlias
                IPv4Address    = @($cfg.IPv4Address | ForEach-Object { [string]$_.IPAddress })
                IPv6Address    = @($cfg.IPv6Address | ForEach-Object { [string]$_.IPAddress })
                IPv4DefaultGW  = @($cfg.IPv4DefaultGateway | ForEach-Object { [string]$_.NextHop })
                IPv6DefaultGW  = @($cfg.IPv6DefaultGateway | ForEach-Object { [string]$_.NextHop })
                DNSServers     = @($cfg.DNSServer | ForEach-Object { [string]$_.ServerAddresses })
            }
        }
    }
} catch {
    $ipCollectionSuccess = $false
    $ipCollectionError = $_.Exception.Message
}

# 4. Route Table Audit (IPv4 and IPv6, All Destinations)
$routeCollectionSuccess = $false
$routeCollectionError = $null
$routes = @()
try {
    $netRoutes = Get-NetRoute -ErrorAction Stop
    $routeCollectionSuccess = $true
    if ($netRoutes) {
        foreach ($route in $netRoutes) {
            $routes += @{
                AddressFamily       = [string]$route.AddressFamily.ToString()
                DestinationPrefix   = [string]$route.DestinationPrefix
                NextHop             = [string]$route.NextHop
                RouteMetric         = [int]$route.RouteMetric
                InterfaceAlias      = [string]$route.InterfaceAlias
                State               = [string]$route.State.ToString()
            }
        }
    }
} catch {
    $routeCollectionSuccess = $false
    $routeCollectionError = $_.Exception.Message
}

# 5. Socket Probes across Defined Protocol/Family Endpoints
$testEndpoints = @(
    @{ Host = "8.8.8.8"; Port = 53; Family = "InterNetwork"; Desc = "Public DNS IPv4" },
    @{ Host = "1.1.1.1"; Port = 80; Family = "InterNetwork"; Desc = "Public Web IPv4" },
    @{ Host = "142.250.190.46"; Port = 443; Family = "InterNetwork"; Desc = "Direct IP HTTPS" },
    @{ Host = "2606:4700:4700::1111"; Port = 53; Family = "InterNetworkV6"; Desc = "Public DNS IPv6" },
    @{ Host = "2001:4860:4860::8888"; Port = 53; Family = "InterNetworkV6"; Desc = "Google DNS IPv6" },
    @{ Host = "127.0.0.1"; Port = 1950; Family = "InterNetwork"; Desc = "Broker Port Loopback" }
)

$socketProbes = @()
foreach ($ep in $testEndpoints) {
    $socketResult = [ordered]@{
        TargetHost   = [string]$ep.Host
        TargetPort   = [int]$ep.Port
        AddressFamily = [string]$ep.Family
        Description  = [string]$ep.Desc
        ProbeStatus  = "UNKNOWN" # NETWORK_DENIED, TIMEOUT, CONNECTED, SETUP_ERROR
        Connected    = $false
        SocketErrorCode = $null
        ErrorMessage = $null
    }

    try {
        $addressFamily = [System.Net.Sockets.AddressFamily]::InterNetwork
        if ($ep.Family -eq "InterNetworkV6") {
            $addressFamily = [System.Net.Sockets.AddressFamily]::InterNetworkV6
        }

        $socket = New-Object System.Net.Sockets.Socket($addressFamily, [System.Net.Sockets.SocketType]::Stream, [System.Net.Sockets.ProtocolType]::Tcp)
        $ipAddress = [System.Net.IPAddress]::Parse($ep.Host)
        $endPoint = New-Object System.Net.IPEndPoint($ipAddress, $ep.Port)

        try {
            $connectAsync = $socket.BeginConnect($endPoint, $null, $null)
            $waitSuccess = $connectAsync.AsyncWaitHandle.WaitOne(1000, $false)
            if ($waitSuccess -and $socket.Connected) {
                $socketResult.Connected = $true
                $socketResult.ProbeStatus = "CONNECTED"
                $socket.EndConnect($connectAsync)
            } else {
                $socketResult.Connected = $false
                $socketResult.ProbeStatus = "TIMEOUT"
                $socketResult.ErrorMessage = "Connection timed out"
            }
        } catch [System.Net.Sockets.SocketException] {
            $socketResult.Connected = $false
            $socketResult.ProbeStatus = "NETWORK_DENIED"
            $socketResult.SocketErrorCode = [int]$_.Exception.SocketErrorCode
            $socketResult.ErrorMessage = $_.Exception.Message
        } catch {
            $socketResult.Connected = $false
            $socketResult.ProbeStatus = "NETWORK_DENIED"
            $socketResult.ErrorMessage = $_.Exception.Message
        } finally {
            $socket.Close()
        }
    } catch {
        # Failure in socket initialization (e.g. IPv6 protocol unsupported on disabled stack)
        $socketResult.Connected = $false
        $socketResult.ProbeStatus = "SETUP_ERROR"
        $socketResult.ErrorMessage = $_.Exception.Message
    }

    $socketProbes += $socketResult
}

# 6. Assemble Comprehensive Telemetry Payload
$endTimeUtc = [DateTime]::UtcNow.ToString("o")

$evidenceReport = [ordered]@{
    ReportType         = "AMIGO_GUEST_CONTAINMENT_STAGE1_PROBE"
    Specification      = "TWO_STAGE_NATIVE_ISOLATION_20261111"
    SessionNonce       = [string]$sessionNonce
    StartTimeUtc       = [string]$startTimeUtc
    EndTimeUtc         = [string]$endTimeUtc
    GuestIdentity      = $guestIdentity
    CollectionStatus   = [ordered]@{
        AdaptersCollected = $adapterCollectionSuccess
        AdapterError      = $adapterCollectionError
        IPConfigsCollected = $ipCollectionSuccess
        IPConfigError     = $ipCollectionError
        RoutesCollected   = $routeCollectionSuccess
        RouteError        = $routeCollectionError
    }
    NetworkAdapters    = $interfaces
    IPConfiguration    = $ipConfiguration
    RouteTable         = $routes
    SocketProbes       = $socketProbes
    IntendedContainment = "Hypervisor-enforced network disconnection awaiting host validation"
    ProbeActionOnly    = $true
}

# 7. Write Structured JSON Artifact
$jsonOutput = $evidenceReport | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($OutputPath, $jsonOutput, [System.Text.Encoding]::UTF8)

Write-Host "Hardened probe audit completed. Telemetry written to: $OutputPath"
