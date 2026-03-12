param(
    [switch]$SkipSync,
    [switch]$SkipInstaller,
    [switch]$InstallInnoSetup
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message"
}

function Get-CommandPath {
    param([string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

function Find-InnoSetup {
    $candidates = @()

    if ($env:ISCC_PATH) {
        $candidates += $env:ISCC_PATH
    }

    foreach ($commandName in @("ISCC.exe", "iscc")) {
        $commandPath = Get-CommandPath $commandName
        if ($commandPath) {
            $candidates += $commandPath
        }
    }

    $localAppData = [System.Environment]::GetEnvironmentVariable("LOCALAPPDATA")
    if (-not $localAppData) {
        $localAppData = Join-Path $HOME "AppData\Local"
    }

    $programFilesX86 = [System.Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
    if (-not $programFilesX86) {
        $programFilesX86 = "C:\Program Files (x86)"
    }

    $programFiles = [System.Environment]::GetEnvironmentVariable("ProgramFiles")
    if (-not $programFiles) {
        $programFiles = "C:\Program Files"
    }

    $candidates += @(
        (Join-Path $localAppData "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path $programFilesX86 "Inno Setup 6\ISCC.exe"),
        (Join-Path $programFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $localAppData "Programs\Inno Setup 5\ISCC.exe"),
        (Join-Path $programFilesX86 "Inno Setup 5\ISCC.exe"),
        (Join-Path $programFiles "Inno Setup 5\ISCC.exe")
    )

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

function Invoke-Step {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

if ($env:OS -ne "Windows_NT") {
    throw "Windows packaging must be run on Windows."
}

$rootDir = Split-Path -Parent $PSScriptRoot
$uvPath = Get-CommandPath "uv"
if (-not $uvPath) {
    throw "uv is required. Install uv first, then rerun this script."
}

$previousSkipInstaller = $env:BOOKCRAWLER_SKIP_INSTALLER
try {
    Set-Location $rootDir

    if (-not $SkipSync) {
        Write-Step "Syncing Python dependencies"
        Invoke-Step $uvPath @("sync", "--extra", "dev", "--extra", "windows")
    }

    if ($SkipInstaller) {
        $env:BOOKCRAWLER_SKIP_INSTALLER = "1"
    }
    else {
        Remove-Item Env:BOOKCRAWLER_SKIP_INSTALLER -ErrorAction SilentlyContinue
        $isccPath = Find-InnoSetup
        if (-not $isccPath) {
            if ($InstallInnoSetup) {
                $wingetPath = Get-CommandPath "winget"
                if (-not $wingetPath) {
                    throw "winget is required to auto-install Inno Setup. Install Inno Setup manually or rerun with -SkipInstaller."
                }

                Write-Step "Installing Inno Setup"
                Invoke-Step $wingetPath @(
                    "install",
                    "--id",
                    "JRSoftware.InnoSetup",
                    "-e",
                    "--silent",
                    "--accept-source-agreements",
                    "--accept-package-agreements"
                )
                $isccPath = Find-InnoSetup
            }

            if (-not $isccPath) {
                throw "Inno Setup compiler was not found. Install it first, rerun with -InstallInnoSetup, or use -SkipInstaller to build only dist/BookCrawling."
            }
        }
    }

    Write-Step "Building Windows package"
    Invoke-Step $uvPath @("run", "--extra", "dev", "--extra", "windows", "scripts/build_windows.py")
}
finally {
    if ($null -eq $previousSkipInstaller) {
        Remove-Item Env:BOOKCRAWLER_SKIP_INSTALLER -ErrorAction SilentlyContinue
    }
    else {
        $env:BOOKCRAWLER_SKIP_INSTALLER = $previousSkipInstaller
    }
}
