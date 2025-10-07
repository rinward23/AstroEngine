; AstroEngine Windows Installer Script aligned with SPEC-02

#define AppName "AstroEngine"
#define AppVersion "1.0.0"
#define AppPublisher "AstroEngine Project"

[Setup]
AppId={{9F4D9B43-4C19-41D1-A3F9-5A0FE2D7B6F1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={code:GetDefaultDir}
DefaultGroupName=AstroEngine
DisableDirPage=no
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=AstroEngine-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional options:";
Name: "firewall"; Description: "Allow AstroEngine through Windows Defender Firewall (ports 8000 & 8501)"; GroupDescription: "Networking:"; Flags: unchecked

[Dirs]
Name: "{app}\var"; Flags: uninsalwaysuninstall
Name: "{app}\logs"; Flags: uninsalwaysuninstall
Name: "{app}\logs\install"; Flags: uninsalwaysuninstall
Name: "{app}\installer\cache"; Flags: uninsalwaysuninstall
Name: "{app}\config"; Flags: uninsalwaysuninstall

[Files]
Source: "..\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\astroengine\*"; DestDir: "{app}\astroengine"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\migrations\*"; DestDir: "{app}\migrations"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\profiles\*"; DestDir: "{app}\profiles"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\rulesets\*"; DestDir: "{app}\rulesets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\schemas\*"; DestDir: "{app}\schemas"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\requirements.lock\*"; DestDir: "{app}\requirements.lock"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\alembic.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\installer\windows_portal_entry.py"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "..\installer\scripts\*"; DestDir: "{app}\installer\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\installer\offline\*"; DestDir: "{app}\installer\offline"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\installer\manifests\*"; DestDir: "{app}\installer\manifests"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\module\developer_platform\submodules\installers\windows_one_click.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\Start AstroEngine"; Filename: "{app}\env\Scripts\python.exe"; Parameters: """{app}\installer\windows_portal_entry.py""" --launch both --wait"; WorkingDir: "{app}"
Name: "{group}\Start API Only"; Filename: "{app}\env\Scripts\python.exe"; Parameters: """{app}\installer\windows_portal_entry.py""" --launch api --wait --no-browser"; WorkingDir: "{app}"
Name: "{group}\Start UI Only"; Filename: "{app}\env\Scripts\python.exe"; Parameters: """{app}\installer\windows_portal_entry.py""" --launch ui --wait"; WorkingDir: "{app}"
Name: "{group}\Repair AstroEngine"; Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File \"{app}\installer\scripts\astroengine_post_install.ps1\" -InstallRoot \"{app}\" -Mode \"{code:GetInstallMode}\" -Scope \"{code:GetInstallScope}\" -InstallPython -LogPath \"{app}\logs\install\repair.log\""; WorkingDir: "{app}"
Name: "{group}\Open Logs Folder"; Filename: "explorer.exe"; Parameters: "\"{app}\\logs\""
Name: "{group}\Open Data Folder"; Filename: "explorer.exe"; Parameters: "\"{app}\\var\""
Name: "{group}\Uninstall AstroEngine"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Start AstroEngine"; Filename: "{app}\env\Scripts\python.exe"; Parameters: """{app}\installer\windows_portal_entry.py""" --launch both"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File \"{app}\installer\scripts\astroengine_post_install.ps1\" -InstallRoot \"{app}\" -Mode \"{code:GetInstallMode}\" -Scope \"{code:GetInstallScope}\"{code:GetSwissArgument}{code:GetFirewallArgument} -ManifestPath \"{app}\installer\manifests\online_python.json\" -LogPath \"{app}\logs\install\post_install.log\""; WorkingDir: "{app}"; Flags: runhidden waituntilterminated

[UninstallDelete]
Type: filesandordirs; Name: "{app}\installer\cache"
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\env"
Type: dirifempty; Name: "{app}\logs"

[Code]
var
  ModePage: TWizardPage;
  OnlineRadio: TNewRadioButton;
  OfflineRadio: TNewRadioButton;
  SwissPage: TInputDirWizardPage;
  SwissSelection: string;

procedure InitializeWizard;
begin
  ModePage := CreateCustomPage(wpLicense, 'Installation Mode', 'Choose how AstroEngine will acquire its Python runtime and dependencies.');

  OnlineRadio := TNewRadioButton.Create(ModePage);
  OnlineRadio.Parent := ModePage.Surface;
  OnlineRadio.Top := 0;
  OnlineRadio.Left := 0;
  OnlineRadio.Width := ModePage.SurfaceWidth;
  OnlineRadio.Caption := 'Online (download verified runtime and wheels during setup)';
  OnlineRadio.Checked := True;

  OfflineRadio := TNewRadioButton.Create(ModePage);
  OfflineRadio.Parent := ModePage.Surface;
  OfflineRadio.Top := OnlineRadio.Top + OnlineRadio.Height + ScaleY(8);
  OfflineRadio.Left := 0;
  OfflineRadio.Width := ModePage.SurfaceWidth;
  OfflineRadio.Caption := 'Offline (use bundled Python runtime and wheel cache)';

  SwissPage := CreateInputDirPage(ModePage.ID, 'Swiss Ephemeris (optional)', 'Import Swiss Ephemeris data', 'If you have the Swiss Ephemeris dataset, select its folder. Leave blank to skip this step.');
  SwissPage.Add('Swiss Ephemeris source folder (optional)');
  SwissSelection := '';
end;

function GetDefaultDir(Param: string): string;
begin
  if IsAdminInstallMode then
    Result := ExpandConstant('{pf}\AstroEngine')
  else
    Result := ExpandConstant('{localappdata}\AstroEngine');
end;

function SelectedInstallMode: string;
begin
  if OfflineRadio.Checked then
    Result := 'Offline'
  else
    Result := 'Online';
end;

function GetInstallMode(Param: string): string;
begin
  Result := SelectedInstallMode;
end;

function GetInstallScope(Param: string): string;
begin
  if IsAdminInstallMode then
    Result := 'AllUsers'
  else
    Result := 'PerUser';
end;

function GetSwissArgument(Param: string): string;
var
  DirValue: string;
begin
  DirValue := Trim(SwissSelection);
  if DirValue = '' then
    Result := ''
  else
    Result := ' -SwissSource ' + AddQuotes(DirValue);
end;

function GetFirewallArgument(Param: string): string;
begin
  if WizardIsTaskSelected('firewall') then
    Result := ' -ConfigureFirewall'
  else
    Result := '';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ModePage.ID then
  begin
    if (not OnlineRadio.Checked) and (not OfflineRadio.Checked) then
    begin
      MsgBox('Select an installation mode before continuing.', mbError, MB_OK);
      Result := False;
    end;
  end
  else if CurPageID = SwissPage.ID then
  begin
    SwissSelection := SwissPage.Values[0];
    if (Trim(SwissSelection) <> '') and (not DirExists(SwissSelection)) then
    begin
      MsgBox('The selected Swiss Ephemeris directory does not exist.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function InitializeUninstall: Boolean;
var
  Response: Integer;
begin
  Result := True;
  Response := MsgBox('Do you want to remove AstroEngine user data (including dev.db and logs)?',
    mbConfirmation, MB_YESNOCANCEL);
  if Response = IDCANCEL then
    Result := False
  else if Response = IDYES then
  begin
    DelTree(ExpandConstant('{app}\var'), True, True, True);
    DelTree(ExpandConstant('{app}\logs'), True, True, True);
    DelTree(ExpandConstant('{userappdata}\AstroEngine'), True, True, True);
    if IsAdminInstallMode then
      DelTree(ExpandConstant('{commonappdata}\AstroEngine'), True, True, True);
  end;
end;
