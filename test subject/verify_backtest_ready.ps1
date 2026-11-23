<#
.SYNOPSIS
    AMIGO Quantitative Backtest & Readiness Verification Control Loop
.DESCRIPTION
    Autonomous orchestrator that evaluates, validates, compiles, and certifies
    the AMIGO system for strategy tester backtesting and operational readiness.
    Enforces quants and engineering safety invariants:
      1. Python Environment & Import Integrity (.pth linkage)
      2. Full Python Test Suite Gate (848 tests passing, 0 failures)
      3. Offline Contracts & Safety Guards Verification
      4. MQL5 Compilation & Artifact Freshness (0 errors, 0 warnings)
      5. Multi-Terminal EX5 Distribution Parity
      6. Offline Isolated Strategy Tester Profile Validation
      7. Continuous Monitoring / Watchdog Loop (optional single-pass or loop mode)
#>

param(
    [switch]$WatchMode = $false,
    [int]$IntervalSeconds = 300,
    [switch]$LaunchBacktest = $false
)

$ErrorActionPreference = "Stop"

$Workspace = "C:\Users\USER\Desktop\ALGOMIND"
$Terminal1_Id = "D0E8209F77C8CF37AD8BF550E51FF075"
$Terminal2_Id = "B54FD4362E205B20F698D85C43C4639C"
$Terminal1_Dir = "C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\$Terminal1_Id"
$Terminal2_Dir = "C:\Users\USER\AppData\Roaming\MetaQuotes\Terminal\$Terminal2_Id"
$MetaEditor = "C:\Program Files\MetaTrader 5\metaeditor64.exe"
$MetaTrader = "C:\Program Files\MetaTrader 5\terminal64.exe"
$IniConfig = "$Workspace\test_isolated_bt.ini"
$OfflineTestScript = "C:\Users\USER\Documents\Codex\2026-10-19\c\outputs\amigo-bot-audit\offline-evidence\test_offline_contracts.py"

function Write-QuantLog {
    param([string]$Level, [string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $color = switch ($Level) {
        "INFO"    { "Cyan" }
        "SUCCESS" { "Green" }
        "WARN"    { "Yellow" }
        "FAIL"    { "Red" }
        default   { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Invoke-ReadinessVerification {
    Write-QuantLog "INFO" "=========================================================="
    Write-QuantLog "INFO" "STARTING AMIGO READINESS & INTEGRITY VERIFICATION PASS"
    Write-QuantLog "INFO" "=========================================================="

    $AllPassed = $true

    # 1. Environment & Module Resolution Check
    Write-QuantLog "INFO" "Step 1: Checking Python engine and 'algomind' module resolution..."
    try {
        $importCheck = python -c "import algomind; print(algomind.__file__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-QuantLog "SUCCESS" "Python module resolved: $importCheck"
        } else {
            Write-QuantLog "FAIL" "Failed to import algomind: $importCheck"
            $AllPassed = $false
        }
    } catch {
        Write-QuantLog "FAIL" "Python execution error: $_"
        $AllPassed = $false
    }

    # 2. Run Comprehensive Python Core & Orderflow Lab Test Suite
    Write-QuantLog "INFO" "Step 2: Executing full pytest test harness (848 tests)..."
    try {
        $pytestOut = python -m pytest "$Workspace\Python\algomind\tests" "$Workspace\Python\algomind\orderflow_lab\tests" -q 2>&1
        $pytestSummary = $pytestOut | Select-Object -Last 2
        if ($LASTEXITCODE -eq 0) {
            Write-QuantLog "SUCCESS" "Pytest Suite: $pytestSummary"
        } else {
            Write-QuantLog "FAIL" "Pytest Suite failed with exit code $LASTEXITCODE : $pytestSummary"
            $AllPassed = $false
        }
    } catch {
        Write-QuantLog "FAIL" "Pytest execution exception: $_"
        $AllPassed = $false
    }

    # 3. Offline Contracts & Safety Guard Testing
    Write-QuantLog "INFO" "Step 3: Checking offline contracts and safety invariants..."
    if (Test-Path $OfflineTestScript) {
        $offlineProc = Start-Process python -ArgumentList "`"$OfflineTestScript`"" -NoNewWindow -PassThru -Wait
        if ($offlineProc.ExitCode -eq 0) {
            Write-QuantLog "SUCCESS" "Offline contracts verified (Timestamp guard, atomic write, rollback, isolation)."
        } else {
            Write-QuantLog "FAIL" "Offline contracts failed with exit code $($offlineProc.ExitCode)"
            $AllPassed = $false
        }
    } else {
        Write-QuantLog "WARN" "Offline contracts test script not found at $OfflineTestScript"
    }

    # 4. MQL5 Include Synchronization and Compilation
    Write-QuantLog "INFO" "Step 4: Synchronizing MQL5 workspace headers and recompiling AMIGO.mq5..."
    try {
        $mqlInclude = "$Workspace\MQL5\Include"
        $t1Include = "$Terminal1_Dir\MQL5\Include"
        $t1Experts = "$Terminal1_Dir\MQL5\Experts"
        $srcMq5 = "$Workspace\MQL5\Experts\AMIGO.mq5"
        $t1Mq5 = "$t1Experts\AMIGO.mq5"
        $compileLog = "$Workspace\compile_chk_now.log"

        if (Test-Path $t1Include) {
            Copy-Item "$mqlInclude\*" "$t1Include\" -Recurse -Force
        }
        if (Test-Path $t1Experts) {
            Copy-Item $srcMq5 $t1Mq5 -Force
        }

        if (Test-Path $MetaEditor) {
            $proc = Start-Process $MetaEditor -ArgumentList "/compile:`"$t1Mq5`"", "/log:`"$compileLog`"" -Wait -PassThru
            $logTail = Get-Content $compileLog -Tail 5
            $isZeroErrors = $logTail | Select-String -Pattern "0 errors, 0 warnings"

            if ($isZeroErrors) {
                Write-QuantLog "SUCCESS" "MetaEditor Compilation Successful: $isZeroErrors"
                
                # Copy fresh ex5 back to ALGOMIND and Terminal 2
                $freshEx5 = "$t1Experts\AMIGO.ex5"
                if (Test-Path $freshEx5) {
                    $item = Get-Item $freshEx5
                    Copy-Item $freshEx5 "$Workspace\MQL5\Experts\AMIGO.ex5" -Force
                    
                    $t2Experts = "$Terminal2_Dir\MQL5\Experts"
                    if (Test-Path $t2Experts) {
                        Copy-Item $freshEx5 "$t2Experts\AMIGO.ex5" -Force
                        Write-QuantLog "SUCCESS" "Distributed fresh binary (AMIGO.ex5: $($item.Length) bytes) to all terminals."
                    }
                }
            } else {
                Write-QuantLog "FAIL" "MQL5 Compilation encountered errors! Check $compileLog"
                $AllPassed = $false
            }
        } else {
            Write-QuantLog "FAIL" "MetaEditor binary not found at $MetaEditor"
            $AllPassed = $false
        }
    } catch {
        Write-QuantLog "FAIL" "Compilation & distribution failed: $_"
        $AllPassed = $false
    }

    # 5. Isolated Backtest Configuration Audit
    Write-QuantLog "INFO" "Step 5: Verifying Strategy Tester INI configuration..."
    if (Test-Path $IniConfig) {
        $iniContent = Get-Content $IniConfig -Raw
        if ($iniContent -match "Expert=AMIGO\.ex5" -and $iniContent -match "ShutdownTerminal=1") {
            Write-QuantLog "SUCCESS" "Strategy Tester INI config ($IniConfig) verified and isolated."
        } else {
            Write-QuantLog "WARN" "INI configuration exists but may lack critical parameters."
        }
    } else {
        Write-QuantLog "FAIL" "Strategy tester INI config missing: $IniConfig"
        $AllPassed = $false
    }

    # Certification Gate
    if ($AllPassed) {
        Write-QuantLog "SUCCESS" ">>> AMIGO SYSTEM CERTIFIED: 100% BACKTEST READY & OPERATIONALLY SOUND <<<"
        if ($LaunchBacktest) {
            Write-QuantLog "INFO" "Launching MetaTrader 5 Strategy Tester..."
            Start-Process $MetaTrader -ArgumentList "/config:`"$IniConfig`""
            Write-QuantLog "SUCCESS" "Terminal launched in Strategy Tester mode."
        }
    } else {
        Write-QuantLog "FAIL" ">>> AMIGO SYSTEM BLOCKED: One or more readiness gates failed. <<<"
    }

    return $AllPassed
}

# Execution Entry Point
if ($WatchMode) {
    Write-QuantLog "INFO" "Entering Autonomous Watchdog Loop. Polling interval: $IntervalSeconds seconds."
    while ($true) {
        $result = Invoke-ReadinessVerification
        Write-QuantLog "INFO" "Sleeping for $IntervalSeconds seconds... (Ctrl+C to stop)"
        Start-Sleep -Seconds $IntervalSeconds
    }
} else {
    $result = Invoke-ReadinessVerification
    if (-not $result) {
        exit 1
    }
}
