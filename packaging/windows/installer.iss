; Build with: iscc packaging\windows\installer.iss
[Setup]
AppName=AstroEngine
AppVersion={#GetFileVersion("..\..\dist\AstroEngine\AstroEngine.exe")}
DefaultDirName={pf}\AstroEngine
DefaultGroupName=AstroEngine
OutputDir=packaging\windows\Output
OutputBaseFilename=AstroEngine-Setup
DisableDirPage=no
DisableProgramGroupPage=no
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\AstroEngine.exe
WizardStyle=modern

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: env; Description: "Set SE_EPHE_PATH environment variable"; GroupDescription: "Environment"; Flags: unchecked

[Files]
Source: "..\..\dist\AstroEngine\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\AstroEngine"; Filename: "{app}\AstroEngine.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\AstroEngine"; Filename: "{app}\AstroEngine.exe"; Tasks:

[Run]
Filename: "{app}\AstroEngine.exe"; Description: "Launch AstroEngine"; Flags: nowait postinstall skipifsilent

[Registry]
; Optionally set a user-level environment variable for ephemeris path
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "SE_EPHE_PATH"; ValueData: "{code:GetEphemerisPath}"; Flags: preservestringtype; Tasks: env

[Code]
var
  EphePage: TInputDirWizardPage;

function GetEphemerisPath(Value: string): string;
begin
  if WizardIsTaskSelected('env') then
    Result := EphePage.Values[0]
  else
    Result := GetEnv('SE_EPHE_PATH');
end;

procedure InitializeWizard;
begin
  EphePage := CreateInputDirPage(wpSelectTasks, 'Swiss Ephemeris Data', 'Optional: select your ephemeris data folder', 'If you have Swiss Ephemeris .se1/.se2 files, choose the folder so the app can find them. You can also set this later in the app under Doctor.', False, 'Folder containing ephemeris files:');
  EphePage.Add('');
end;
