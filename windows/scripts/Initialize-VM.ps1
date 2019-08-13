function Install-Chocolatey {
    # Run the installer
    Set-ExecutionPolicy Bypass -Scope Process -Force; Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))

    # Turn off confirmation
    choco feature enable -n allowGlobalConfirmation
}

# Install Windows .NET Features
Install-WindowsFeature -Name NET-Framework-Features -IncludeAllSubFeature
Install-WindowsFeature -Name NET-Framework-45-Features -IncludeAllSubFeature

Write-Host "Install chocolatey"
Install-Chocolatey

# Disable antivirus analysis on C:
Set-MpPreference -ScanAvgCPULoadFactor 5 -ExclusionPath "C:\"