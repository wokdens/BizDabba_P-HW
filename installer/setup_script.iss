; Inno Setup Script for BizDibba Diwali v2.0
; Powered by wokdens.com

#define MyAppName "BizDibba Diwali v2.0"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "wokdens.com"
#define MyAppURL "https://wokdens.com"
#define MyAppExeName "BizDibba_Diwali_v2.0.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Using a dedicated AppId guarantees side-by-side coexistence with any other software.
AppId={{D37F8E1A-7C2B-4A19-9E54-8B39F025C671}
AppName={#MyAppName} by wokdens.com
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName} by wokdens.com
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=BizDibba_Diwali_v2.0_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no

; Version Info embedded into Setup.exe
VersionInfoVersion=2.0.0.0
VersionInfoCompany=wokdens.com
VersionInfoDescription=BizDibba Diwali v2.0 Installation Wizard
VersionInfoCopyright=Copyright (C) 2026 Powered by wokdens.com
VersionInfoProductName=BizDibba Diwali v2.0 by wokdens.com

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\BizDibba_Diwali_v2.0\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\certificates\wokdens_codesign.cer"; DestDir: "{app}\certificates"; Flags: ignoreversion
Source: "..\scripts\install_certificate.bat"; DestDir: "{app}"; DestName: "Register_Security_Certificate.bat"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Auto-register certificate into Current User Trusted Publishers store silently
Filename: "certutil.exe"; Parameters: "-user -addstore -f ""TrustedPublisher"" ""{app}\certificates\wokdens_codesign.cer"""; Flags: runhidden waituntilterminated
; Launch application option
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent


