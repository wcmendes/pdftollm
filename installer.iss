; PDF2LLM — Inno Setup Script
; Gera um Setup.exe profissional para Windows
;
; Pré-requisitos:
;   1. Ter a pasta dist\PDF2LLM\ já gerada (pdfconverter_folder.spec)
;   2. Instalar Inno Setup: https://jrsoftware.org/isinfo.php
;
; Uso:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
;
; Ou via GitHub Actions (veja release.yml)

#define MyAppName "PDF2LLM"
#define MyAppVersion "0.1.0-beta"
#define MyAppPublisher "William Mendes"
#define MyAppURL "https://github.com/wcmendes/pdftollm"
#define MyAppExeName "PDF2LLM.exe"

[Setup]
AppId={{A3F7B2C1-9D4E-4F6A-8B5C-1E2D3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=PDF2LLM-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\PDF2LLM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
