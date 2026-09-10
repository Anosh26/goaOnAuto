# ==============================================================================
# GoaOnAuto - Complete Context Menu Unregistration Script
# Single Responsibility: Cleanly removes all GoaOnAuto and legacy context menu
# registry keys from Folders, Folder Backgrounds, and SystemFileAssociations.
# ==============================================================================

$targetPaths = @(
    "HKCU:\Software\Classes\Directory\shell\GoaOnAuto",
    "HKCU:\Software\Classes\Directory\Background\shell\GoaOnAuto",
    "HKCU:\Software\Classes\Directory\shell\GenerateDeclaration",
    "HKCU:\Software\Classes\Directory\Background\shell\GenerateDeclaration"
)

foreach ($path in $targetPaths) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
        Write-Host "🗑️ Removed context menu from: $path"
    } else {
        Write-Host "ℹ️ Key not present: $path"
    }
}

$imageFormats = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")
foreach ($fmt in $imageFormats) {
    $imgKeys = @(
        "HKCU:\Software\Classes\SystemFileAssociations\$fmt\shell\GoaOnAuto",
        "HKCU:\Software\Classes\SystemFileAssociations\$fmt\shell\ProcessImage"
    )
    foreach ($k in $imgKeys) {
        if (Test-Path $k) {
            Remove-Item -Path $k -Recurse -Force
            Write-Host "🗑️ Removed image context menu from: $k"
        }
    }
}

Write-Host "`n✅ All GoaOnAuto context menus successfully unregistered."
