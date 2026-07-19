# Get the absolute path to the compiled executable
$binPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\bin\process_image.exe")

if (-not (Test-Path $binPath)) {
    Write-Error "Executable not found at $binPath. Please compile the C project first."
    Exit 1
}

$formats = @(".jpg", ".jpeg", ".png")

foreach ($format in $formats) {
    $registryPath = "HKCU:\Software\Classes\SystemFileAssociations\$format\shell\ProcessImage"
    $commandPath = "$registryPath\command"
    
    # Create registry paths if they don't exist
    if (-not (Test-Path $registryPath)) {
        New-Item -Path $registryPath -Force | Out-Null
    }
    if (-not (Test-Path $commandPath)) {
        New-Item -Path $commandPath -Force | Out-Null
    }
    
    # Set context menu label and command execution string
    Set-ItemProperty -Path $registryPath -Name "(Default)" -Value "Process Photo (GoaOnAuto)"
    Set-ItemProperty -Path $commandPath -Name "(Default)" -Value "`"$binPath`" `"%1`""
    
    Write-Host "Registered 'Process Photo (GoaOnAuto)' context menu for $format"
}

Write-Host "Context menu registration complete!"
