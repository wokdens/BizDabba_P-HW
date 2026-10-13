$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\sobti_ewvfrji\Desktop\BizDabba for Paint & Hardware.lnk")
$Shortcut.TargetPath = "C:\Users\sobti_ewvfrji\Desktop\BizDabba for Paint & Hardware\BizDabba_PHWP.exe"
$Shortcut.WorkingDirectory = "C:\Users\sobti_ewvfrji\Desktop\BizDabba for Paint & Hardware"
$Shortcut.Description = "BizDabba for Paint & Hardware by Wokdens.com"
$Shortcut.Save()

# Also update the old shortcut if it exists
if (Test-Path "C:\Users\sobti_ewvfrji\Desktop\BizDabba PHWP.lnk") {
    $Old = $WshShell.CreateShortcut("C:\Users\sobti_ewvfrji\Desktop\BizDabba PHWP.lnk")
    $Old.TargetPath = "C:\Users\sobti_ewvfrji\Desktop\BizDabba for Paint & Hardware\BizDabba_PHWP.exe"
    $Old.WorkingDirectory = "C:\Users\sobti_ewvfrji\Desktop\BizDabba for Paint & Hardware"
    $Old.Save()
}

Write-Host "Desktop shortcuts created and updated successfully!"
