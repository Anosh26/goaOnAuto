# Get the absolute path to GUI PowerShell script
$guiPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\gui\process_image_gui.ps1")

if (-not (Test-Path $guiPath)) {
    Write-Error "GUI script not found at $guiPath."
    Exit 1
}

$formats = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")

foreach ($format in $formats) {
    $registryPath = "HKCU:\Software\Classes\SystemFileAssociations\$format\shell\ProcessImage"
    $commandPath = "$registryPath\command"
    
    if (-not (Test-Path $registryPath)) {
        New-Item -Path $registryPath -Force | Out-Null
    }
    if (-not (Test-Path $commandPath)) {
        New-Item -Path $commandPath -Force | Out-Null
    }
    
    Set-ItemProperty -Path $registryPath -Name "(Default)" -Value "Process Photo (GoaOnAuto)"
    Set-ItemProperty -Path $registryPath -Name "Icon" -Value "shell32.dll,-301" -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $commandPath -Name "(Default)" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$guiPath`" `"%1`""
    
    Write-Host "Registered 'Process Photo (GoaOnAuto)' context menu for $format"
}

Write-Host "Context menu registration complete!"
