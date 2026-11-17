; Script Inno Setup per generare un vero pacchetto Setup_CasaLavoroOutreach.exe
; Apri questo file con Inno Setup Compiler (https://jrsoftware.org/isinfo.php) e premi Compile.

#define MyAppName "CasaLavoroPRO & XPart"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CasaLavoroPRO"
#define MyAppExeName "CasaLavoroOutreach.exe"

[Setup]
AppId={{8F4C2B10-9D3A-4E77-B5F1-434153414C41}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\CasaLavoroOutreach
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist_setup
OutputBaseFilename=Setup_CasaLavoroOutreach
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "CasaLavoroOutreach.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env"; DestDir: "{app}"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "artigiani_estratti.csv"; DestDir: "{app}"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "registro_contattati.csv"; DestDir: "{app}"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "xpart_ricambi_estratti.csv"; DestDir: "{app}"; Flags: onlyifdoesntexist skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
