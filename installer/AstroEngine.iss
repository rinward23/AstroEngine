; Build with Inno Setup (iscc.exe)
#define AppName "AstroEngine"
#define AppVersion "1.0.0"
#define Publisher "Your Company"
#define InstallDirName "{localappdata}\AstroEngine"
#define ExeSrcDir "..\dist\AstroEngine"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={#InstallDirName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=AstroEngine-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "{#ExeSrcDir}\AstroEngine.exe"; DestDir: "{app}"; Flags: ignoreversion
; Optional: ship CLI too
Source: "..\dist\astroengine-cli\astroengine-cli.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AstroEngine"; Filename: "{app}\AstroEngine.exe"
Name: "{userdesktop}\AstroEngine"; Filename: "{app}\AstroEngine.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\AstroEngine.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
