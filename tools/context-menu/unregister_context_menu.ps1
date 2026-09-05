$formats = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")

foreach ($format in $formats) {
    $registryPath = "HKCU:\Software\Classes\SystemFileAssociations\$format\shell\ProcessImage"
    
    if (Test-Path $registryPath) {
        Remove-Item -Path $registryPath -Recurse -Force
        Write-Host "Unregistered context menu for $format"
    }
}

Write-Host "Context menu cleanup complete!"
