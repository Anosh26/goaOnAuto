# ==============================================================================
# GoaOnAuto - Cascading Context Menu Registration Redirector
# Delegates directly to the comprehensive register_unified_context_menu.ps1
# to ensure all parts (Declarations + Background Remover) are registered.
# ==============================================================================

$unifiedScript = Join-Path $PSScriptRoot "register_unified_context_menu.ps1"
if (Test-Path $unifiedScript) {
    & $unifiedScript
} else {
    Write-Error "Unified registration script not found at $unifiedScript"
}
