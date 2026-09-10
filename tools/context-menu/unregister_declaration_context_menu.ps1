# ==============================================================================
# GoaOnAuto - Context Menu Unregistration Redirector
# Delegates directly to unregister_unified_context_menu.ps1 to cleanly
# remove all GoaOnAuto context menus.
# ==============================================================================

$unregScript = Join-Path $PSScriptRoot "unregister_unified_context_menu.ps1"
if (Test-Path $unregScript) {
    & $unregScript
} else {
    Write-Error "Unregistration script not found at $unregScript"
}
