<#
.SYNOPSIS
Prepare the Windows RPC client from this source checkout, without py.exe.
.DESCRIPTION
Uses an existing CPython 3.11 64-bit installation. No system Python installer is
downloaded or run. Existing incompatible/incomplete virtual environments are
left untouched. Run once, or again only when Python dependencies change.
.PARAMETER PythonPath
Optional full path to an existing CPython 3.11 64-bit python.exe. Quote paths
containing spaces. An explicit incompatible path fails instead of falling back.
.EXAMPLE
.\setup_client.bat
.EXAMPLE
.\setup_client.bat -PythonPath "C:\Users\Trader\AppData\Local\Programs\Python\Python311\python.exe"
.LINK
https://docs.python.org/3.11/using/windows.html
.LINK
https://www.python.org/downloads/release/python-3119/
#>
[CmdletBinding()]
param([string]$PythonPath = "")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-CompatiblePython {
    param([string]$Executable)

    if ([string]::IsNullOrWhiteSpace($Executable)) {
        return $null
    }

    # Windows Store aliases can open the Store instead of running an interpreter.
    if ($Executable -match '(?i)[\\/]Microsoft[\\/]WindowsApps[\\/]python(?:3)?\.exe$') {
        return $null
    }
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        return $null
    }

    try {
        $resolved = (Resolve-Path -LiteralPath $Executable).Path
        # Use Python single quotes so Windows PowerShell 5.1's native argument
        # marshalling does not strip embedded double quotes from the -c program.
        $probe = "import json,struct,sys; print(json.dumps({'version': list(sys.version_info[:2]), 'bits': struct.calcsize('P') * 8, 'implementation': sys.implementation.name}))"
        $output = @(& $resolved -c $probe 2>$null)
        if ($LASTEXITCODE -ne 0 -or $output.Count -eq 0) {
            return $null
        }
        $runtime = $output[-1] | ConvertFrom-Json
        if ($runtime.implementation -ne "cpython" -or $runtime.version[0] -ne 3 -or $runtime.version[1] -ne 11 -or $runtime.bits -ne 64) {
            return $null
        }
        return [pscustomobject]@{ Executable = $resolved; Runtime = $runtime }
    }
    catch {
        return $null
    }
}

function Find-CompatiblePython {
    $candidates = New-Object 'System.Collections.Generic.List[string]'

    if ($env:LOCALAPPDATA) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'))
    }
    if ($env:ProgramFiles) {
        $candidates.Add((Join-Path $env:ProgramFiles 'Python311\python.exe'))
    }
    if ($env:ProgramW6432) {
        $candidates.Add((Join-Path $env:ProgramW6432 'Python311\python.exe'))
    }
    if ($env:SystemDrive) {
        $candidates.Add((Join-Path ($env:SystemDrive + '\') 'Python311\python.exe'))
    }

    # Official installers register their location even when PATH was not changed.
    foreach ($hive in @('HKCU', 'HKLM')) {
        if (Get-PSDrive -Name $hive -ErrorAction SilentlyContinue) {
            $key = $hive + ':\Software\Python\PythonCore\3.11\InstallPath'
            if (Test-Path -LiteralPath $key) {
                $location = Get-Item -LiteralPath $key
                $registeredExe = $location.GetValue('ExecutablePath')
                $registeredDir = $location.GetValue('')
                if ($registeredExe) {
                    $candidates.Add([string]$registeredExe)
                }
                if ($registeredDir) {
                    $candidates.Add((Join-Path ([string]$registeredDir) 'python.exe'))
                }
            }
        }
    }

    foreach ($name in @('python.exe', 'python3.exe', 'python3.11.exe', 'python', 'python3', 'python3.11')) {
        foreach ($command in @(Get-Command -Name $name -CommandType Application -All -ErrorAction SilentlyContinue)) {
            $candidates.Add($command.Source)
        }
    }
    foreach ($candidate in @($candidates | Select-Object -Unique)) {
        $compatible = Get-CompatiblePython -Executable $candidate
        if ($null -ne $compatible) {
            return $compatible
        }
    }
    return $null
}

function Show-PythonInstallHelp {
    Write-Host 'No compatible CPython 3.11 64-bit installation was found.'
    Write-Host 'Install Python yourself using ONE of these methods, then rerun setup_client.bat:'
    Write-Host '  Official installer: https://www.python.org/downloads/release/python-3119/'
    Write-Host '  Choose Windows installer (64-bit). Python 3.11.9 is the last 3.11 release with this Windows installer.'
    Write-Host '  Or, if winget is available:'
    Write-Host '    winget install --exact --id Python.Python.3.11 --architecture x64'
    Write-Host 'A Python launcher (py.exe) and changing PATH are optional for this script.'
    Write-Host 'For a custom location:'
    Write-Host '  .\setup_client.bat -PythonPath "C:\path\to\Python311\python.exe"'
    Write-Host 'Official Windows documentation: https://docs.python.org/3.11/using/windows.html'
}

function Invoke-CheckedPython {
    param([string]$Executable, [string[]]$PythonArguments)

    & $Executable @PythonArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE. Setup stopped; fix the preceding error and rerun."
    }
}

try {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $clientScript = Join-Path $repoRoot 'examples\client_server\run_windows_client.py'
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'pyproject.toml')) -or -not (Test-Path -LiteralPath $clientScript)) {
        throw 'Run setup_client.bat from a complete vn.py Git checkout containing the Windows RPC client.'
    }

    Push-Location -LiteralPath $repoRoot
    try {
        $explicitPython = $null
        if (-not [string]::IsNullOrWhiteSpace($PythonPath)) {
            $explicitPython = Get-CompatiblePython -Executable $PythonPath
            if ($null -eq $explicitPython) {
                throw 'PythonPath must point to a working CPython 3.11 64-bit python.exe. No packages were installed.'
            }
        }

        $venvDir = Join-Path $repoRoot '.venv'
        $venvPython = Join-Path $venvDir 'Scripts\python.exe'
        if ($env:OS -eq 'Windows_NT' -and (Test-Path -LiteralPath $venvPython)) {
            $runningClient = Get-CimInstance Win32_Process | Where-Object {
                $_.ExecutablePath -ieq $venvPython -and $_.CommandLine -match 'run_windows_client\.py'
            }
            if ($runningClient) {
                throw 'Close the running Windows Trader window before changing client dependencies.'
            }
        }
        if (Test-Path -LiteralPath $venvDir) {
            $existingPython = Get-CompatiblePython -Executable $venvPython
            if ($null -eq $existingPython) {
                throw 'The existing .venv is incomplete or is not CPython 3.11 64-bit. It was not replaced. Close the client, inspect/back up the environment, and move it aside before retrying.'
            }
            Write-Host "Reusing $venvPython"
        }
        else {
            $basePython = $explicitPython
            if ($null -eq $basePython) {
                $basePython = Find-CompatiblePython
            }
            if ($null -eq $basePython) {
                Show-PythonInstallHelp
                throw 'Install CPython 3.11 64-bit, then rerun setup_client.bat.'
            }
            Write-Host "Creating .venv with $($basePython.Executable)"
            Invoke-CheckedPython -Executable $basePython.Executable -PythonArguments @('-m', 'venv', $venvDir)
            if ($null -eq (Get-CompatiblePython -Executable $venvPython)) {
                throw 'Virtual environment creation did not produce a compatible .venv\Scripts\python.exe. Setup stopped.'
            }
        }

        Invoke-CheckedPython -Executable $venvPython -PythonArguments @('-m', 'pip', 'install', '--upgrade', 'pip', 'wheel')
        Invoke-CheckedPython -Executable $venvPython -PythonArguments @('-m', 'pip', 'install', '-e', $repoRoot)
        Invoke-CheckedPython -Executable $venvPython -PythonArguments @('-m', 'pip', 'install', 'vnpy_rpcservice==1.1.0')
        Invoke-CheckedPython -Executable $venvPython -PythonArguments @('-m', 'pip', 'check')

        # Import GUI classes without constructing a QApplication or starting Trader.
        $smoke = "import pathlib,sys; import vnpy; from vnpy.trader.ui import MainWindow; from vnpy_rpcservice import RpcGateway; assert pathlib.Path(vnpy.__file__).resolve().is_relative_to(pathlib.Path(sys.argv[1]).resolve()), 'vnpy is not importing from this editable checkout'; print('Verified vnpy UI and RpcGateway imports from the editable checkout.')"
        Invoke-CheckedPython -Executable $venvPython -PythonArguments @('-c', $smoke, $repoRoot)

        Write-Host 'Client environment is ready. No GUI was launched.'
        Write-Host 'Start the client: .\.venv\Scripts\python.exe examples\client_server\run_windows_client.py'
        Write-Host 'Later Python UI updates: close Trader, then run .\update_client.bat.'
    }
    finally {
        Pop-Location
    }
    exit 0
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
