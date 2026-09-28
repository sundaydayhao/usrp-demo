$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$uhdRoot = 'C:\Program Files\UHD'
if (-not (Test-Path -LiteralPath "$uhdRoot\bin\uhd_usrp_probe.exe")) {
    throw 'UHD is not installed. Run scripts\install-uhd.ps1 as administrator first.'
}
$env:UHD_PKG_PATH = $uhdRoot
$env:UHD_LIBRARY_PATH = "$uhdRoot\bin"
$env:UHD_IMAGES_DIR = "$uhdRoot\share\uhd\images"
$env:PATH = "$projectRoot\.venv\Scripts;$uhdRoot\bin;$uhdRoot\lib\uhd\examples;$uhdRoot\lib\uhd\utils;$env:PATH"
Write-Output "USRP tools: $uhdRoot"
Write-Output "Python: $projectRoot\.venv\Scripts\python.exe"
