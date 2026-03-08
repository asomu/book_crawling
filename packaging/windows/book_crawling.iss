#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef StageDir
  #define StageDir "..\\..\\dist\\BookCrawling"
#endif
#ifndef BootstrapperPath
  #define BootstrapperPath "..\\..\\build\\windows\\staging\\MicrosoftEdgeWebView2Setup.exe"
#endif
#ifndef SetupIconPath
  #define SetupIconPath "..\\..\\build\\windows\\staging\\book.ico"
#endif

[Setup]
AppId={{B8A536D9-2C59-4E52-83CE-FBFF72310A12}
AppName=Book Crawling v2
AppVersion={#AppVersion}
AppPublisher=Book Crawling
DefaultDirName={localappdata}\Programs\BookCrawling
DefaultGroupName=Book Crawling
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename=BookCrawlingSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#SetupIconPath}
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\BookCrawling.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#BootstrapperPath}"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autoprograms}\Book Crawling"; Filename: "{app}\BookCrawling.exe"
Name: "{autodesktop}\Book Crawling"; Filename: "{app}\BookCrawling.exe"; Tasks: desktopicon

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; Parameters: "/silent /install"; Flags: runhidden waituntilterminated; StatusMsg: "Installing Microsoft WebView2 Runtime..."; Check: NeedsWebView2Runtime
Filename: "{app}\BookCrawling.exe"; Description: "Launch Book Crawling"; Flags: nowait postinstall skipifsilent

[Code]
function HasWebView2Runtime(): Boolean;
var
  Version: string;
  Key: string;
begin
  Key := 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result :=
    (RegQueryStringValue(HKLM64, Key, 'pv', Version) and (Version <> '')) or
    (RegQueryStringValue(HKLM32, Key, 'pv', Version) and (Version <> '')) or
    (RegQueryStringValue(HKCU, Key, 'pv', Version) and (Version <> ''));
end;

function NeedsWebView2Runtime(): Boolean;
begin
  Result := not HasWebView2Runtime();
end;
