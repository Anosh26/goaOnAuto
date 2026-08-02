# Get the absolute path to GUI PowerShell script
$guiPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\process_image_gui.ps1")

if (-not (Test-Path $guiPath)) {
    Write-Error "GUI script not found at $guiPath."
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
    Set-ItemProperty -Path $commandPath -Name "(Default)" -Value "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$guiPath`" `"%1`""
    
    Write-Host "Registered 'Process Photo (GoaOnAuto)' context menu for $format"
}

Write-Host "Context menu registration complete!"
