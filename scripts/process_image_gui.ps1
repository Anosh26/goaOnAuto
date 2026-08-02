param(
    [string]$inputPath = ""
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

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
$binPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\bin\process_image.exe")
$aiScriptPath = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\src\image_processor\ai_remove_bg.py")

# Create Main Form (Dark Modern Theme)
$form = New-Object System.Windows.Forms.Form
$form.Text = "GoaOnAuto - Photo Processing Settings"
$form.Size = New-Object System.Drawing.Size(460, 420)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(24, 24, 27)
$form.ForeColor = [System.Drawing.Color]::White

# Title Header
$lblHeader = New-Object System.Windows.Forms.Label
$lblHeader.Text = "Process Photo: $inputFilename"
$lblHeader.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$lblHeader.Location = New-Object System.Drawing.Point(20, 15)
$lblHeader.Size = New-Object System.Drawing.Size(400, 25)
$lblHeader.ForeColor = [System.Drawing.Color]::FromArgb(59, 130, 246)
$form.Controls.Add($lblHeader)

# --- Target File Size Section ---
$grpSize = New-Object System.Windows.Forms.GroupBox
$grpSize.Text = "Target Maximum File Size (KB)"
$grpSize.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$grpSize.Location = New-Object System.Drawing.Point(20, 50)
$grpSize.Size = New-Object System.Drawing.Size(400, 120)
$grpSize.ForeColor = [System.Drawing.Color]::FromArgb(228, 228, 231)
$grpSize.BackColor = [System.Drawing.Color]::FromArgb(39, 39, 42)

# Quick Preset Buttons
$btn50 = New-Object System.Windows.Forms.Button
$btn50.Text = "50 KB (Portal)"
$btn50.Size = New-Object System.Drawing.Size(85, 28)
$btn50.Location = New-Object System.Drawing.Point(15, 25)
$btn50.FlatStyle = "Flat"
$btn50.BackColor = [System.Drawing.Color]::FromArgb(59, 130, 246)
$btn50.ForeColor = [System.Drawing.Color]::White

$btn100 = New-Object System.Windows.Forms.Button
$btn100.Text = "100 KB"
$btn100.Size = New-Object System.Drawing.Size(75, 28)
$btn100.Location = New-Object System.Drawing.Point(110, 25)
$btn100.FlatStyle = "Flat"
$btn100.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn100.ForeColor = [System.Drawing.Color]::White

$btn200 = New-Object System.Windows.Forms.Button
$btn200.Text = "200 KB"
$btn200.Size = New-Object System.Drawing.Size(75, 28)
$btn200.Location = New-Object System.Drawing.Point(195, 25)
$btn200.FlatStyle = "Flat"
$btn200.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn200.ForeColor = [System.Drawing.Color]::White

$btn500 = New-Object System.Windows.Forms.Button
$btn500.Text = "500 KB"
$btn500.Size = New-Object System.Drawing.Size(75, 28)
$btn500.Location = New-Object System.Drawing.Point(280, 25)
$btn500.FlatStyle = "Flat"
$btn500.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btn500.ForeColor = [System.Drawing.Color]::White

$grpSize.Controls.Add($btn50)
$grpSize.Controls.Add($btn100)
$grpSize.Controls.Add($btn200)
$grpSize.Controls.Add($btn500)

# Trackbar / Slider
$slider = New-Object System.Windows.Forms.TrackBar
$slider.Minimum = 20
$slider.Maximum = 500
$slider.Value = 50
$slider.TickFrequency = 50
$slider.Location = New-Object System.Drawing.Point(15, 65)
$slider.Size = New-Object System.Drawing.Size(280, 45)
$grpSize.Controls.Add($slider)

# Slider Value Display Label
$lblSliderVal = New-Object System.Windows.Forms.Label
$lblSliderVal.Text = "50 KB"
$lblSliderVal.Font = New-Object System.Drawing.Font("Segoe UI", 11, [System.Drawing.FontStyle]::Bold)
$lblSliderVal.Location = New-Object System.Drawing.Point(305, 68)
$lblSliderVal.Size = New-Object System.Drawing.Size(80, 30)
$lblSliderVal.ForeColor = [System.Drawing.Color]::FromArgb(96, 165, 250)
$grpSize.Controls.Add($lblSliderVal)

$slider.Add_ValueChanged({
    $lblSliderVal.Text = "$($slider.Value) KB"
})

$btn50.Add_Click({ $slider.Value = 50 })
$btn100.Add_Click({ $slider.Value = 100 })
$btn200.Add_Click({ $slider.Value = 200 })
$btn500.Add_Click({ $slider.Value = 500 })

$form.Controls.Add($grpSize)

# --- AI & Options Group ---
$grpOpt = New-Object System.Windows.Forms.GroupBox
$grpOpt.Text = "Processing Engine & Scaling"
$grpOpt.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$grpOpt.Location = New-Object System.Drawing.Point(20, 180)
$grpOpt.Size = New-Object System.Drawing.Size(400, 110)
$grpOpt.ForeColor = [System.Drawing.Color]::FromArgb(228, 228, 231)
$grpOpt.BackColor = [System.Drawing.Color]::FromArgb(39, 39, 42)

$chkAI = New-Object System.Windows.Forms.CheckBox
$chkAI.Text = "Use AI Human & Clothing Segmentation (rembg - GPU/CPU)"
$chkAI.Font = New-Object System.Drawing.Font("Segoe UI", 8.5)
$chkAI.Checked = $true
$chkAI.Location = New-Object System.Drawing.Point(15, 25)
$chkAI.Size = New-Object System.Drawing.Size(370, 25)
$chkAI.ForeColor = [System.Drawing.Color]::FromArgb(161, 161, 170)
$grpOpt.Controls.Add($chkAI)

$lblScale = New-Object System.Windows.Forms.Label
$lblScale.Text = "Resolution:"
$lblScale.Font = New-Object System.Drawing.Font("Segoe UI", 8.5)
$lblScale.Location = New-Object System.Drawing.Point(15, 63)
$lblScale.Size = New-Object System.Drawing.Size(80, 20)
$grpOpt.Controls.Add($lblScale)

$cmbScale = New-Object System.Windows.Forms.ComboBox
$cmbScale.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
$cmbScale.Items.Add("50% Downscale (Recommended for Portals)")
$cmbScale.Items.Add("100% Original Resolution")
$cmbScale.SelectedIndex = 0
$cmbScale.Location = New-Object System.Drawing.Point(100, 60)
$cmbScale.Size = New-Object System.Drawing.Size(280, 25)
$grpOpt.Controls.Add($cmbScale)

$form.Controls.Add($grpOpt)

# Progress Status Label
$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = "Ready to process photo."
$lblStatus.Font = New-Object System.Drawing.Font("Segoe UI", 8.5, [System.Drawing.FontStyle]::Italic)
$lblStatus.Location = New-Object System.Drawing.Point(20, 300)
$lblStatus.Size = New-Object System.Drawing.Size(400, 20)
$lblStatus.ForeColor = [System.Drawing.Color]::FromArgb(161, 161, 170)
$form.Controls.Add($lblStatus)

# Process Button
$btnProcess = New-Object System.Windows.Forms.Button
$btnProcess.Text = "⚡ Process Photo"
$btnProcess.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$btnProcess.Size = New-Object System.Drawing.Size(190, 40)
$btnProcess.Location = New-Object System.Drawing.Point(20, 325)
$btnProcess.FlatStyle = "Flat"
$btnProcess.BackColor = [System.Drawing.Color]::FromArgb(37, 99, 235)
$btnProcess.ForeColor = [System.Drawing.Color]::White

# Cancel Button
$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "Cancel"
$btnCancel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$btnCancel.Size = New-Object System.Drawing.Size(190, 40)
$btnCancel.Location = New-Object System.Drawing.Point(230, 325)
$btnCancel.FlatStyle = "Flat"
$btnCancel.BackColor = [System.Drawing.Color]::FromArgb(63, 63, 70)
$btnCancel.ForeColor = [System.Drawing.Color]::White

$btnCancel.Add_Click({ $form.Close() })

$btnProcess.Add_Click({
    $btnProcess.Enabled = $false
    $btnCancel.Enabled = $false
    $targetKB = $slider.Value

    $tempPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "ai_temp_$([System.IO.Path]::GetFileNameWithoutExtension($inputPath)).png")
    $finalOutput = [System.IO.Path]::Combine([System.IO.Path]::GetDirectoryName($inputPath), "$([System.IO.Path]::GetFileNameWithoutExtension($inputPath))_processed.jpg")

    $currentInput = $inputPath
    $skipCbg = ""

    if ($chkAI.Checked) {
        $lblStatus.Text = "Running AI Background Removal (NVIDIA GPU / CPU)..."
        $form.Refresh()

        $pyProc = Start-Process -FilePath "python" -ArgumentList "`"$aiScriptPath`" `"$inputPath`" `"$tempPath`"" -NoNewWindow -PassThru -Wait
        if ($pyProc.ExitCode -eq 0 -and (Test-Path $tempPath)) {
            $currentInput = $tempPath
            $skipCbg = "--skip-bg-remove"
        } else {
            $lblStatus.Text = "AI failed or rembg unavailable. Falling back to C flood-fill engine..."
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
