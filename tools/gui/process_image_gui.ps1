param(
    [string]$inputPath = ""
)

# Enable Native Win32 Per-Monitor High DPI Awareness to eliminate blurry text on 1080p screens
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WinDpi {
    [DllImport("shcore.dll")]
    public static extern int SetProcessDpiAwareness(int awareness);
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
}
"@
try {
    [void][WinDpi]::SetProcessDpiAwareness(2) # 2 = PROCESS_PER_MONITOR_DPI_AWARE
} catch {
    try { [WinDpi]::SetProcessDPIAware() } catch {}
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()
[System.Windows.Forms.Application]::SetCompatibleTextRenderingDefault($false)

if (-not $inputPath -or -not (Test-Path $inputPath)) {
    # If no file was passed via command line, open file picker dialog
    $filePicker = New-Object System.Windows.Forms.OpenFileDialog
    $filePicker.Filter = "Image Files (*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png"
    $filePicker.Title = "Select Photo to Process (GoaOnAuto)"
    if ($filePicker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $inputPath = $filePicker.FileName
    } else {
        Exit 0
    }
}

$inputFilename = [System.IO.Path]::GetFileName($inputPath)
$binPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\..\bin\process_image.exe")
$aiScriptPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\..\python\vision\ai_remove_bg.py")

# Resolve Python binary (read .env or default to system Python with AI packages)
$envPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\..\.env")
$pythonBin = "python"
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -match '^PYTHON_BIN\s*=\s*["'']?(.*?)["'']?\s*$') {
            $candidate = $matches[1]
            if (Test-Path $candidate) {
                $pythonBin = $candidate
            }
        }
    }
}
if ($pythonBin -eq "python") {
    $knownPython = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    if (Test-Path $knownPython) {
        $pythonBin = $knownPython
    }
}

# Forward to Modern Raylib GPU Background Removal GUI
$raylibGui = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\..\python\gui\bg_remover_gui.py")
if (Test-Path $raylibGui) {
    Start-Process -FilePath $pythonBin -ArgumentList "`"$raylibGui`" `"$inputPath`""
    Exit 0
}

# Helper to load JetBrains Mono Nerd Font / JetBrains Mono / Cascadia Code / Consolas / Segoe UI
function Get-PreferredFont {
    param(
        [float]$size = 10,
        [string]$style = "Regular"
    )
    $styleEnum = [System.Drawing.FontStyle]::$style
    $candidates = @("JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", "JetBrains Mono", "Cascadia Code", "Consolas", "Segoe UI")
    foreach ($cand in $candidates) {
        try {
            $f = New-Object System.Drawing.Font($cand, $size, $styleEnum)
            if ($f.Name -eq $cand) {
                return $f
            }
        } catch {}
    }
    return New-Object System.Drawing.Font("Segoe UI", $size, $styleEnum)
}

# Create Main Form (Optimized for 1920x1080 Laptop Display)
$form = New-Object System.Windows.Forms.Form
$form.Text = "GoaOnAuto - Photo Processing Settings (1080p Full HD)"
$form.Size = New-Object System.Drawing.Size(720, 650)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(24, 24, 27)
$form.ForeColor = [System.Drawing.Color]::White
$form.Font = Get-PreferredFont -size 10 -style "Regular"

# Title Header
$lblHeader = New-Object System.Windows.Forms.Label
$lblHeader.Text = "📷 Process Photo: $inputFilename"
$lblHeader.Font = Get-PreferredFont -size 14 -style "Bold"
$lblHeader.Location = New-Object System.Drawing.Point(25, 20)
$lblHeader.Size = New-Object System.Drawing.Size(650, 32)
$lblHeader.ForeColor = [System.Drawing.Color]::FromArgb(59, 130, 246)
$form.Controls.Add($lblHeader)

# --- Target File Size Section (1080p Layout) ---
$grpSize = New-Object System.Windows.Forms.GroupBox
$grpSize.Text = " Target Maximum File Size (High Resolution Selection)"
$grpSize.Font = Get-PreferredFont -size 11 -style "Bold"
$grpSize.Location = New-Object System.Drawing.Point(25, 62)
$grpSize.Size = New-Object System.Drawing.Size(650, 175)
$grpSize.ForeColor = [System.Drawing.Color]::FromArgb(228, 228, 231)
$grpSize.BackColor = [System.Drawing.Color]::FromArgb(39, 39, 42)

# Quick Preset Buttons Row
$btn30 = New-Object System.Windows.Forms.Button
$btn30.Text = "30 KB"
$btn30.Font = Get-PreferredFont -size 10
$btn30.Size = New-Object System.Drawing.Size(85, 32)
$btn30.Location = New-Object System.Drawing.Point(20, 32)
$btn30.FlatStyle = "Flat"
$btn30.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn30.ForeColor = [System.Drawing.Color]::White

$btn50 = New-Object System.Windows.Forms.Button
$btn50.Text = "50 KB (Portal)"
$btn50.Font = Get-PreferredFont -size 10 -style "Bold"
$btn50.Size = New-Object System.Drawing.Size(130, 32)
$btn50.Location = New-Object System.Drawing.Point(115, 32)
$btn50.FlatStyle = "Flat"
$btn50.BackColor = [System.Drawing.Color]::FromArgb(59, 130, 246)
$btn50.ForeColor = [System.Drawing.Color]::White

$btn100 = New-Object System.Windows.Forms.Button
$btn100.Text = "100 KB"
$btn100.Font = Get-PreferredFont -size 10
$btn100.Size = New-Object System.Drawing.Size(90, 32)
$btn100.Location = New-Object System.Drawing.Point(255, 32)
$btn100.FlatStyle = "Flat"
$btn100.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn100.ForeColor = [System.Drawing.Color]::White

$btn200 = New-Object System.Windows.Forms.Button
$btn200.Text = "200 KB"
$btn200.Font = Get-PreferredFont -size 10
$btn200.Size = New-Object System.Drawing.Size(90, 32)
$btn200.Location = New-Object System.Drawing.Point(355, 32)
$btn200.FlatStyle = "Flat"
$btn200.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn200.ForeColor = [System.Drawing.Color]::White

$btn500 = New-Object System.Windows.Forms.Button
$btn500.Text = "500 KB"
$btn500.Font = Get-PreferredFont -size 10
$btn500.Size = New-Object System.Drawing.Size(90, 32)
$btn500.Location = New-Object System.Drawing.Point(455, 32)
$btn500.FlatStyle = "Flat"
$btn500.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn500.ForeColor = [System.Drawing.Color]::White

$btn1000 = New-Object System.Windows.Forms.Button
$btn1000.Text = "1 MB"
$btn1000.Font = Get-PreferredFont -size 10
$btn1000.Size = New-Object System.Drawing.Size(75, 32)
$btn1000.Location = New-Object System.Drawing.Point(555, 32)
$btn1000.FlatStyle = "Flat"
$btn1000.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn1000.ForeColor = [System.Drawing.Color]::White

$grpSize.Controls.Add($btn30)
$grpSize.Controls.Add($btn50)
$grpSize.Controls.Add($btn100)
$grpSize.Controls.Add($btn200)
$grpSize.Controls.Add($btn500)
$grpSize.Controls.Add($btn1000)

# Trackbar / Slider (High Resolution: 10 to 2000 KB)
$slider = New-Object System.Windows.Forms.TrackBar
$slider.Minimum = 10
$slider.Maximum = 2000
$slider.Value = 50
$slider.TickFrequency = 100
$slider.SmallChange = 1
$slider.LargeChange = 25
$slider.Location = New-Object System.Drawing.Point(15, 105)
$slider.Size = New-Object System.Drawing.Size(460, 50)
$grpSize.Controls.Add($slider)

# Direct Numeric Input Box (Type exact KB value)
$numTargetKB = New-Object System.Windows.Forms.NumericUpDown
$numTargetKB.Minimum = 10
$numTargetKB.Maximum = 2000
$numTargetKB.Value = 50
$numTargetKB.Font = Get-PreferredFont -size 13 -style "Bold"
$numTargetKB.Location = New-Object System.Drawing.Point(490, 110)
$numTargetKB.Size = New-Object System.Drawing.Size(95, 36)
$numTargetKB.BackColor = [System.Drawing.Color]::FromArgb(24, 24, 27)
$numTargetKB.ForeColor = [System.Drawing.Color]::FromArgb(96, 165, 250)
$grpSize.Controls.Add($numTargetKB)

$lblKbUnit = New-Object System.Windows.Forms.Label
$lblKbUnit.Text = "KB"
$lblKbUnit.Font = Get-PreferredFont -size 12 -style "Bold"
$lblKbUnit.Location = New-Object System.Drawing.Point(592, 117)
$lblKbUnit.Size = New-Object System.Drawing.Size(45, 30)
$lblKbUnit.ForeColor = [System.Drawing.Color]::FromArgb(96, 165, 250)
$grpSize.Controls.Add($lblKbUnit)

# Sync Slider and NumericUpDown
$updatingControls = $false

$slider.Add_ValueChanged({
    if (-not $script:updatingControls) {
        $script:updatingControls = $true
        $numTargetKB.Value = $slider.Value
        $script:updatingControls = $false
    }
})

function Update-PresetHighlights([int]$val) {
    $activeBg = [System.Drawing.Color]::FromArgb(59, 130, 246)
    $inactiveBg = [System.Drawing.Color]::FromArgb(63, 63, 70)
    $btn30.BackColor = if ($val -eq 30) { $activeBg } else { $inactiveBg }
    $btn50.BackColor = if ($val -eq 50) { $activeBg } else { $inactiveBg }
    $btn100.BackColor = if ($val -eq 100) { $activeBg } else { $inactiveBg }
    $btn200.BackColor = if ($val -eq 200) { $activeBg } else { $inactiveBg }
    $btn500.BackColor = if ($val -eq 500) { $activeBg } else { $inactiveBg }
    $btn1000.BackColor = if ($val -eq 1000) { $activeBg } else { $inactiveBg }
}

$numTargetKB.Add_ValueChanged({
    if (-not $script:updatingControls) {
        $script:updatingControls = $true
        $slider.Value = [int]$numTargetKB.Value
        Update-PresetHighlights ([int]$numTargetKB.Value)
        $script:updatingControls = $false
    }
})

$btn30.Add_Click({ $numTargetKB.Value = 30 })
$btn50.Add_Click({ $numTargetKB.Value = 50 })
$btn100.Add_Click({ $numTargetKB.Value = 100 })
$btn200.Add_Click({ $numTargetKB.Value = 200 })
$btn500.Add_Click({ $numTargetKB.Value = 500 })
$btn1000.Add_Click({ $numTargetKB.Value = 1000 })

$form.Controls.Add($grpSize)

# --- AI & Options Group ---
$grpOpt = New-Object System.Windows.Forms.GroupBox
$grpOpt.Text = " AI Neural Engine & Absolute Subject Separation"
$grpOpt.Font = Get-PreferredFont -size 11 -style "Bold"
$grpOpt.Location = New-Object System.Drawing.Point(25, 250)
$grpOpt.Size = New-Object System.Drawing.Size(650, 220)
$grpOpt.ForeColor = [System.Drawing.Color]::FromArgb(228, 228, 231)
$grpOpt.BackColor = [System.Drawing.Color]::FromArgb(39, 39, 42)

$chkAI = New-Object System.Windows.Forms.CheckBox
$chkAI.Text = "Use AI Human & Clothing Segmentation (NVIDIA RTX 4060 GPU)"
$chkAI.Font = Get-PreferredFont -size 10.5 -style "Bold"
$chkAI.Checked = $true
$chkAI.Location = New-Object System.Drawing.Point(20, 32)
$chkAI.Size = New-Object System.Drawing.Size(610, 28)
$chkAI.ForeColor = [System.Drawing.Color]::FromArgb(147, 197, 253)
$grpOpt.Controls.Add($chkAI)

$chkCrisp = New-Object System.Windows.Forms.CheckBox
$chkCrisp.Text = "Strict Crisp Binarized Cutoff (Optional)"
$chkCrisp.Font = Get-PreferredFont -size 10
$chkCrisp.Checked = $false
$chkCrisp.Location = New-Object System.Drawing.Point(20, 68)
$chkCrisp.Size = New-Object System.Drawing.Size(610, 28)
$chkCrisp.ForeColor = [System.Drawing.Color]::FromArgb(216, 180, 254)
$grpOpt.Controls.Add($chkCrisp)

$lblModel = New-Object System.Windows.Forms.Label
$lblModel.Text = "AI Model:"
$lblModel.Font = Get-PreferredFont -size 10.5
$lblModel.Location = New-Object System.Drawing.Point(20, 115)
$lblModel.Size = New-Object System.Drawing.Size(100, 28)
$grpOpt.Controls.Add($lblModel)

$cmbModel = New-Object System.Windows.Forms.ComboBox
$cmbModel.Font = Get-PreferredFont -size 10
$cmbModel.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
[void]$cmbModel.Items.Add("u2net_human_seg (Full Human Silhouette, Traps & Chest Model)")
[void]$cmbModel.Items.Add("u2net (General Object Model)")
[void]$cmbModel.Items.Add("u2netp (Lite Fast Model)")
$cmbModel.SelectedIndex = 0
$cmbModel.Location = New-Object System.Drawing.Point(130, 112)
$cmbModel.Size = New-Object System.Drawing.Size(500, 30)
$grpOpt.Controls.Add($cmbModel)

$lblScale = New-Object System.Windows.Forms.Label
$lblScale.Text = "Resolution:"
$lblScale.Font = Get-PreferredFont -size 10.5
$lblScale.Location = New-Object System.Drawing.Point(20, 163)
$lblScale.Size = New-Object System.Drawing.Size(100, 28)
$grpOpt.Controls.Add($lblScale)

$cmbScale = New-Object System.Windows.Forms.ComboBox
$cmbScale.Font = Get-PreferredFont -size 10
$cmbScale.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
[void]$cmbScale.Items.Add("50% Downscale (Recommended for Document Portals)")
[void]$cmbScale.Items.Add("100% Original Resolution")
$cmbScale.SelectedIndex = 0
$cmbScale.Location = New-Object System.Drawing.Point(130, 160)
$cmbScale.Size = New-Object System.Drawing.Size(500, 30)
$grpOpt.Controls.Add($cmbScale)

$form.Controls.Add($grpOpt)

# Progress Status Label
$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = "Ready to process photo."
$lblStatus.Font = Get-PreferredFont -size 10 -style "Italic"
$lblStatus.Location = New-Object System.Drawing.Point(25, 482)
$lblStatus.Size = New-Object System.Drawing.Size(650, 25)
$lblStatus.ForeColor = [System.Drawing.Color]::FromArgb(161, 161, 170)
$form.Controls.Add($lblStatus)

# Process Button
$btnProcess = New-Object System.Windows.Forms.Button
$btnProcess.Text = "⚡ Process Photo"
$btnProcess.Font = Get-PreferredFont -size 12 -style "Bold"
$btnProcess.Size = New-Object System.Drawing.Size(310, 48)
$btnProcess.Location = New-Object System.Drawing.Point(25, 520)
$btnProcess.FlatStyle = "Flat"
$btnProcess.BackColor = [System.Drawing.Color]::FromArgb(37, 99, 235)
$btnProcess.ForeColor = [System.Drawing.Color]::White

# Cancel Button
$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "Cancel"
$btnCancel.Font = Get-PreferredFont -size 11
$btnCancel.Size = New-Object System.Drawing.Size(310, 48)
$btnCancel.Location = New-Object System.Drawing.Point(365, 520)
$btnCancel.FlatStyle = "Flat"
$btnCancel.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btnCancel.ForeColor = [System.Drawing.Color]::White

$btnCancel.Add_Click({ $form.Close() })

$btnProcess.Add_Click({
    $btnProcess.Enabled = $false
    $btnCancel.Enabled = $false
    $targetKB = [int]$numTargetKB.Value

    $tempPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "ai_temp_$([System.IO.Path]::GetFileNameWithoutExtension($inputPath)).png")
    $finalOutput = [System.IO.Path]::Combine([System.IO.Path]::GetDirectoryName($inputPath), "$([System.IO.Path]::GetFileNameWithoutExtension($inputPath))_processed.jpg")

    $currentInput = $inputPath
    $skipCbg = ""

    if ($chkAI.Checked) {
        $lblStatus.Text = "Running High-Precision Human Silhouette AI Segmentation (RTX 4060 GPU)..."
        $form.Refresh()

        $modelArg = switch ($cmbModel.SelectedIndex) {
            1 { "u2net" }
            2 { "u2netp" }
            default { "u2net_human_seg" }
        }
        # Isolate Python from foreign environment variables (e.g. LibreOffice PYTHONPATH)
        if ($env:PYTHONPATH) { Remove-Item env:PYTHONPATH -ErrorAction SilentlyContinue }
        if ($env:PYTHONHOME) { Remove-Item env:PYTHONHOME -ErrorAction SilentlyContinue }

        $pyArgs = "-E `"$aiScriptPath`" `"$inputPath`" `"$tempPath`" --model $modelArg"
        if ($chkCrisp.Checked) {
            $pyArgs += " --crisp"
        }

        $pyProc = Start-Process -FilePath $pythonBin -ArgumentList $pyArgs -NoNewWindow -PassThru -Wait
        if ($pyProc.ExitCode -eq 0 -and (Test-Path $tempPath)) {
            $currentInput = $tempPath
            $skipCbg = "--skip-bg-remove"
        } else {
            $lblStatus.Text = "AI engine failed. Falling back to C flood-fill engine..."
            $form.Refresh()
        }
    }

    $lblStatus.Text = "Resizing & compressing to max $targetKB KB..."
    $form.Refresh()

    $cArgs = @("--max-kb", "$targetKB")
    if ($skipCbg) { $cArgs += "--skip-bg-remove" }
    
    if ($cmbScale.SelectedIndex -eq 1) {
        # 100% original dimensions
        try {
            $img = [System.Drawing.Image]::FromFile($inputPath)
            $cArgs += "--width"
            $cArgs += "$($img.Width)"
            $cArgs += "--height"
            $cArgs += "$($img.Height)"
            $img.Dispose()
        } catch {}
    }

    $cArgs += "`"$currentInput`""
    $cArgs += "`"$finalOutput`""

    $cProc = Start-Process -FilePath $binPath -ArgumentList $cArgs -NoNewWindow -PassThru -Wait

    # Cleanup temporary AI output file
    if (Test-Path $tempPath) { Remove-Item $tempPath -Force }

    if (Test-Path $finalOutput) {
        $finalSizeKB = [math]::Round(((Get-Item $finalOutput).Length / 1KB), 1)
        [System.Windows.Forms.MessageBox]::Show(
            "Photo successfully processed!`n`nOutput Saved: $finalOutput`nFinal File Size: $finalSizeKB KB",
            "GoaOnAuto - Success",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        )
        $form.Close()
    } else {
        [System.Windows.Forms.MessageBox]::Show(
            "Processing failed. Check executable or logs.",
            "GoaOnAuto - Error",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        )
        $btnProcess.Enabled = $true
        $btnCancel.Enabled = $true
    }
})

$form.Controls.Add($btnProcess)
$form.Controls.Add($btnCancel)

[void]$form.ShowDialog()
