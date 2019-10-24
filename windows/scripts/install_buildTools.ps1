$ErrorActionPreference = 'Stop'

$path = "${env:Temp}\buildTools.zip"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
(New-Object System.Net.WebClient).DownloadFile('https://github.com/SonarSource/buildTools/archive/docker.zip', $path)

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($path, 'C:\')

del $path
