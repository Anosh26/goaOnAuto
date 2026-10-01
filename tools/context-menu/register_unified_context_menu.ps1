# ==============================================================================
# GoaOnAuto - Complete Unified Cascading Context Menu Registration
# Single Responsibility: Registers the comprehensive "GoaOnAuto" right-click
# cascading menu across Folders, Folder Backgrounds, and Image Files under HKCU.
# Includes all 4 tools:
#   1. 🏛️ Residence Certificate Declaration
#   2. 📜 OBC Certificate Declaration
#   3. ⚖️ Divergence Certificate Declaration
#   ---
#   4. 🎨 Background Remover & Photo Optimizer (<50KB)
# ==============================================================================

$projectRoot = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\..")
$automationScript = Join-Path $projectRoot "src\automation\extractAndDeclare.ts"
$portalScript = Join-Path $projectRoot "src\automation\fillResidencePortal.ts"
$ocrScript = Join-Path $projectRoot "src\scanner\runOcrScanner.ts"
$bgRemoverScript = Join-Path $projectRoot "python\gui\bg_remover_gui.py"

if (-not (Test-Path $automationScript)) {
    Write-Error "Automation script not found at $automationScript"
    Exit 1
}

if (-not (Test-Path $portalScript)) {
    Write-Error "Portal filler script not found at $portalScript"
    Exit 1
}

if (-not (Test-Path $ocrScript)) {
    Write-Error "OCR scanner script not found at $ocrScript"
    Exit 1
}

# Resolve Bun binary (fully qualified to prevent PATH lookup failures)
$bunPath = (Get-Command bun -ErrorAction SilentlyContinue).Source
if (-not $bunPath -or -not (Test-Path $bunPath)) {
    $userBun = Join-Path $env:USERPROFILE ".bun\bin\bun.exe"
    if (Test-Path $userBun) {
        $bunPath = $userBun
    } else {
        $bunPath = "bun.exe"
    }
}

# Resolve Python binary (fully qualified)
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath -or -not (Test-Path $pythonPath)) {
    $localPy = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    if (Test-Path $localPy) {
        $pythonPath = $localPy
    } else {
        $pythonPath = "python.exe"
    }
}

# Resolve TSX binary for Playwright execution (Node-based runner required for Playwright on Windows)
$tsxPath = Join-Path $projectRoot "node_modules\.bin\tsx.exe"
if (-not (Test-Path $tsxPath)) {
    $cmdTsx = (Get-Command tsx -ErrorAction SilentlyContinue).Source
    if ($cmdTsx) {
        $tsxPath = $cmdTsx
    } else {
        $tsxPath = "npx.cmd tsx"
    }
}

# 1. Clean up all legacy fragmented or partial context menus
$legacyKeys = @(
    "HKCU:\Software\Classes\Directory\shell\GenerateDeclaration",
    "HKCU:\Software\Classes\Directory\Background\shell\GenerateDeclaration",
    "HKCU:\Software\Classes\Directory\shell\GoaOnAuto",
    "HKCU:\Software\Classes\Directory\Background\shell\GoaOnAuto"
)
foreach ($legacy in $legacyKeys) {
    if (Test-Path $legacy) {
        Remove-Item -Path $legacy -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$imageFormats = @(".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")
foreach ($fmt in $imageFormats) {
    $legacyKeysImg = @(
        "HKCU:\Software\Classes\SystemFileAssociations\$fmt\shell\ProcessImage",
        "HKCU:\Software\Classes\SystemFileAssociations\$fmt\shell\GoaOnAuto"
    )
    foreach ($k in $legacyKeysImg) {
        if (Test-Path $k) {
            Remove-Item -Path $k -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

# 2. Define Menu Actions
$subActions = @(
    @{
        Id = "0_ScanOCR"
        Title = "🔍 Scan & Classify Documents (OCR)"
        CommandType = "ocr"
        Icon = "imageres.dll,-98"
        SeparatorBefore = $false
    },
    @{
        Id = "1_Residence"
        Title = "🏛️ Residence Certificate Declaration"
        CommandType = "bun"
        ArgType = "residence"
        Icon = "imageres.dll,-1002"
        SeparatorBefore = $false
    },
    @{
        Id = "2_OBC"
        Title = "📜 OBC Certificate Declaration"
        CommandType = "bun"
        ArgType = "obc"
        Icon = "imageres.dll,-102"
        SeparatorBefore = $false
    },
    @{
        Id = "3_Divergence"
        Title = "⚖️ Divergence Certificate Declaration"
        CommandType = "bun"
        ArgType = "divergence"
        Icon = "imageres.dll,-112"
        SeparatorBefore = $false
    },
    @{
        Id = "4_BgRemover"
        Title = "🎨 Background Remover & Photo Optimizer (<50KB)"
        CommandType = "python"
        ArgType = "bg_remover"
        Icon = "imageres.dll,-71"
        SeparatorBefore = $true
    },
    @{
        Id = "5_PortalResidence"
        Title = "🌐 Auto-Fill GoaOnline Residence Form"
        CommandType = "portal"
        ArgType = "residence"
        Icon = "imageres.dll,-25"
        SeparatorBefore = $true
    }
)

# 3. Target Context Scopes (Folders, Backgrounds, Image Files)
$targetScopes = @(
    @{
        Scope = "Folders"
        BasePath = "HKCU:\Software\Classes\Directory\shell\GoaOnAuto"
        ParamPlaceholder = "%1"
    },
    @{
        Scope = "Folder Background"
        BasePath = "HKCU:\Software\Classes\Directory\Background\shell\GoaOnAuto"
        ParamPlaceholder = "%V"
    }
)

# Add image file associations
foreach ($fmt in $imageFormats) {
    $targetScopes += @{
        Scope = "Image File ($fmt)"
        BasePath = "HKCU:\Software\Classes\SystemFileAssociations\$fmt\shell\GoaOnAuto"
        ParamPlaceholder = "%1"
    }
}

# 4. Register Unified Menus
foreach ($scope in $targetScopes) {
    $basePath = $scope.BasePath
    $argTarget = $scope.ParamPlaceholder

    if (-not (Test-Path $basePath)) {
        New-Item -Path $basePath -Force | Out-Null
    }

    Set-ItemProperty -Path $basePath -Name "MUIVerb" -Value "GoaOnAuto"
    Set-ItemProperty -Path $basePath -Name "SubCommands" -Value ""
    Set-ItemProperty -Path $basePath -Name "Icon" -Value "imageres.dll,-5308" -ErrorAction SilentlyContinue

    $subShellPath = Join-Path $basePath "shell"
    if (-not (Test-Path $subShellPath)) {
        New-Item -Path $subShellPath -Force | Out-Null
    }

    foreach ($action in $subActions) {
        $itemPath = Join-Path $subShellPath $action.Id
        $cmdPath = Join-Path $itemPath "command"

        if (-not (Test-Path $itemPath)) {
            New-Item -Path $itemPath -Force | Out-Null
        }
        if (-not (Test-Path $cmdPath)) {
            New-Item -Path $cmdPath -Force | Out-Null
        }

        Set-ItemProperty -Path $itemPath -Name "MUIVerb" -Value $action.Title
        if ($action.Icon) {
            Set-ItemProperty -Path $itemPath -Name "Icon" -Value $action.Icon -ErrorAction SilentlyContinue
        }

        if ($action.SeparatorBefore) {
            Set-ItemProperty -Path $itemPath -Name "CommandFlags" -Value 32 -Type DWord -ErrorAction SilentlyContinue
        }

        if ($action.CommandType -eq "ocr") {
            $cmdString = "cmd.exe /c start `"GoaOnAuto - Document OCR Scanner`" cmd.exe /k `"`"$tsxPath`" `"$ocrScript`" --dir `"$argTarget`"`""
        } elseif ($action.CommandType -eq "portal") {
            $cmdString = "cmd.exe /c start `"GoaOnAuto - Portal Automation`" cmd.exe /k `"`"$tsxPath`" `"$portalScript`" --dir `"$argTarget`"`""
        } elseif ($action.CommandType -eq "bun") {
            $cmdString = "`"$bunPath`" `"$automationScript`" --type $($action.ArgType) --dir `"$argTarget`""
        } else {
            $cmdString = "`"$pythonPath`" `"$bgRemoverScript`" `"$argTarget`""
        }

        Set-ItemProperty -Path $cmdPath -Name "(Default)" -Value $cmdString
    }
}

Write-Host "`n🎉 Success! Unified 'GoaOnAuto' right-click menu registered across all targets."
Write-Host "   Locations:"
Write-Host "   - Folders (Right-click any folder)"
Write-Host "   - Folder Background (Right-click inside any directory)"
Write-Host "   - Image Files (.jpg, .jpeg, .png, .webp, .bmp, .tiff)"
Write-Host "`n   Menu Items:"
Write-Host "   0. 🔍 Scan & Classify Documents (OCR)"
Write-Host "   1. 🏛️ Residence Certificate Declaration"
Write-Host "   2. 📜 OBC Certificate Declaration"
Write-Host "   3. ⚖️ Divergence Certificate Declaration"
Write-Host "   ---------------------------------------"
Write-Host "   4. 🎨 Background Remover & Photo Optimizer (<50KB)"
Write-Host "   ---------------------------------------"
Write-Host "   5. 🌐 Auto-Fill GoaOnline Residence Form"
