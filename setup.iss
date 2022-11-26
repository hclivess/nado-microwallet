[Setup]
AppName=NADO MicroWallet
AppVersion=[bn1]
DefaultDirName={pf}\NADO MicroWallet
DefaultGroupName=NADO
UninstallDisplayIcon={app}\microwallet.exe
Compression=lzma2
SolidCompression=yes
OutputBaseFilename=NADO_MicroWallet_setup
SetupIconFile=graphics\icon.ico
DisableDirPage=no

WizardImageFile=graphics\left.bmp
WizardSmallImageFile=graphics\mini.bmp

[Files]
Source: "microwallet.dist\*" ; DestDir: "{app}"; Flags: recursesubdirs;

[Icons]
Name: "{group}\NADO MicroWallet"; Filename: "{app}\microwallet.exe"
Name: "{group}\Uninstall NADO MicroWallet"; Filename: "{uninstallexe}"

Name: "{commondesktop}\NADO MicroWallet"; Filename: "{app}\microwallet.exe"

[Registry]
; keys for 32-bit systems
Root: HKCU32; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"; ValueType: String; ValueName: "{app}\microwallet.exe"; ValueData: "RUNASADMIN"; Flags: uninsdeletekeyifempty uninsdeletevalue; Check: not IsWin64
Root: HKLM32; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"; ValueType: String; ValueName: "{app}\microwallet.exe"; ValueData: "RUNASADMIN"; Flags: uninsdeletekeyifempty uninsdeletevalue; Check: not IsWin64

; keys for 64-bit systems
Root: HKCU64; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"; ValueType: String; ValueName: "{app}\microwallet.exe"; ValueData: "RUNASADMIN"; Flags: uninsdeletekeyifempty uninsdeletevalue; Check: IsWin64
Root: HKLM64; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"; ValueType: String; ValueName: "{app}\microwallet.exe"; ValueData: "RUNASADMIN"; Flags: uninsdeletekeyifempty uninsdeletevalue; Check: IsWin64


[Run]
Filename: "{app}\microwallet.exe"; Description: "Run NADO MicroWallet"; Flags: shellexec postinstall skipifsilent unchecked
