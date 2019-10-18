Write-Host "Finalize VM configuration"

$currentPath = (Get-ItemProperty -Path 'Registry::HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session Manager\Environment' -Name PATH).Path
$updatedPath = $currentPath+';C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\MSBuild\15.0\Bin;c:\buildTools-docker\bin'

Set-ItemProperty -Path 'Registry::HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session Manager\Environment' -Name PATH -Value $updatedPath