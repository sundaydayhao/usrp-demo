$ErrorActionPreference = 'Stop'
$logPath = 'C:\projects\usrp-demo\logs\install-uhd.txt'
Start-Transcript -Path $logPath -Force
try {
    $installer = 'C:\projects\usrp-demo\downloads\uhd_4.10.0.0-release_Win64_VS2022.exe'
    $expected = '1C75C18288705136A76F4766187CD68CAC1774597B025C897B88CF153DEBD336'
    if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $expected) { throw 'Installer hash mismatch' }
    if ((Get-AuthenticodeSignature -LiteralPath $installer).Status -ne 'Valid') { throw 'Installer signature is invalid' }
    $process = Start-Process -FilePath $installer -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    Write-Output "UHD installer exit code: $($process.ExitCode)"
    if ($process.ExitCode -notin 0,3010) { throw "UHD installation failed: $($process.ExitCode)" }
    & pnputil.exe /add-driver 'C:\Program Files\UHD\share\uhd\usbdriver\erllc_uhd_usrp1.inf' /install
    $driverExit = $LASTEXITCODE
    Write-Output "USRP1 driver exit code: $driverExit"
    if ($driverExit -notin 0,3010) { throw "Driver installation failed: $driverExit" }
    Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\VID_FFFE&PID_0002\*' } | Format-List Status,Class,FriendlyName,InstanceId,Problem
    'SUCCESS' | Set-Content -LiteralPath 'C:\projects\usrp-demo\logs\install-result.txt'
} catch {
    $_ | Out-String | Set-Content -LiteralPath 'C:\projects\usrp-demo\logs\install-result.txt'
    throw
} finally {
    Stop-Transcript
}
