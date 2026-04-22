[Setup]
AppName=VIGILE
AppVersion=1.0.0
AppPublisher=Francis NDAYUBAHA
AppPublisherURL=https://github.com/ton-username/Vigile-1.0
DefaultDirName={autopf}\VIGILE
DefaultGroupName=VIGILE
OutputDir=installer_output
OutputBaseFilename=VigileSetup-1.0.0
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
UninstallDisplayIcon={app}\Vigile.exe
LicenseFile=
PrivilegesRequired=lowest

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; \
  GroupDescription: "Icônes supplémentaires :"; Flags: unchecked

[Files]
Source: "dist\Vigile\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\VIGILE"; Filename: "{app}\Vigile.exe"
Name: "{group}\Désinstaller VIGILE"; Filename: "{uninstallexe}"
Name: "{commondesktop}\VIGILE"; Filename: "{app}\Vigile.exe"; \
  Tasks: desktopicon

[Run]
Filename: "{app}\Vigile.exe"; Description: "Lancer VIGILE"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
