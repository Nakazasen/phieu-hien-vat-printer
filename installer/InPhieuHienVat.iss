; Build after: py package_app.py
; Compile with Inno Setup 6: ISCC installer\InPhieuHienVat.iss

#define AppName "In Phiếu Hiện Vật"
#define AppVersion "0.1.1"
#define AppPublisher "KDTVN"
#define AppId "{{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}"
#define LauncherExe "InPhieuHienVat_Launcher.exe"
#define BundleDir "..\release_artifacts\install_bundle"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
SetupIconFile=..\app_icon.ico
DefaultDirName={localappdata}\InPhieuHienVat
DefaultGroupName={#AppName}
OutputDir=..\release_artifacts
OutputBaseFilename=InPhieuHienVat_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}

[Languages]
; Vietnamese.isl is an optional Inno Setup language component and is not
; included by every compiler installation. Default.isl keeps the installer
; reproducibly buildable; the installed application itself is Vietnamese.
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#LauncherExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#LauncherExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Tạo lối tắt trên màn hình nền"; GroupDescription: "Lối tắt bổ sung:"

[Run]
Filename: "{app}\{#LauncherExe}"; Description: "Khởi chạy {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.staging"
