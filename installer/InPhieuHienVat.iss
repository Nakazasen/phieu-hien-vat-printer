; Trình cài đặt Windows ban đầu cho In Phiếu Hiện Vật
; Biên dịch bằng Inno Setup 6 sau khi chạy: py package_app.py
; Cài bộ ứng dụng onedir theo phiên bản; máy đích không cần cài Python.

#define AppName "In Phiếu Hiện Vật"
#define AppVersion "0.1.2"
#define AppPublisher "KDTVN"
#define AppId "{{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}}"
#define LauncherExe "InPhieuHienVat_Launcher.exe"
#define BundleDir "..\release_artifacts\install_bundle"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
SetupIconFile=..\app_icon.ico
; Cài theo người dùng vì apps/<version>, current.json và .staging là trạng thái cập nhật
; có thể thay đổi, thuộc quyền sở hữu của người dùng thông thường.
DefaultDirName={localappdata}\InPhieuHienVat
DefaultGroupName={#AppName}
OutputDir=..\release_artifacts
OutputBaseFilename=InPhieuHienVat_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}

[Languages]
; Bản dịch tiếng Việt được kiểm tra tương thích Inno Setup 6.5.0+
Name: "vietnamese"; MessagesFile: "languages\Vietnamese.isl"

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
; Dữ liệu vận hành trong LocalAppData (InPhieuHienVatData) không bao giờ bị xóa tại đây.
Type: filesandordirs; Name: "{app}\.staging"
