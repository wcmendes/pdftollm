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
#define TesseractURL "https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe"

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

[Types]
Name: "full"; Description: "Instalação completa (com Tesseract OCR)"
Name: "compact"; Description: "Instalação mínima (sem Tesseract)"
Name: "custom"; Description: "Personalizada"; Flags: iscustom

[Components]
Name: "main"; Description: "PDF2LLM - Aplicação principal"; Types: full compact custom; Flags: fixed
Name: "tesseract"; Description: "Tesseract OCR 5.5 (recomendado - melhora OCR em PDFs escaneados)"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\PDF2LLM\*"; DestDir: "{app}"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function IsTesseractInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf}\Tesseract-OCR\tesseract.exe')) or
            FileExists(ExpandConstant('{commonpf32}\Tesseract-OCR\tesseract.exe')) or
            FileExists(ExpandConstant('{localappdata}\Tesseract-OCR\tesseract.exe'));
end;

procedure InstallTesseract;
var
  TempFile: String;
  ResultCode: Integer;
  DownloadCmd: String;
begin
  if IsTesseractInstalled then
  begin
    Log('Tesseract já instalado, pulando.');
    Exit;
  end;

  TempFile := ExpandConstant('{tmp}\tesseract-setup.exe');
  
  // Usa PowerShell para baixar (disponível em qualquer Windows 10+)
  DownloadCmd := 'powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri ''{#TesseractURL}'' -OutFile ''' + TempFile + ''' }"';
  
  WizardForm.StatusLabel.Caption := 'Baixando Tesseract OCR (~35 MB)...';
  WizardForm.StatusLabel.Update;
  
  if not Exec('cmd.exe', '/C ' + DownloadCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('Não foi possível baixar o Tesseract OCR.' + #13#10 +
           'O PDF2LLM funcionará usando EasyOCR como alternativa.' + #13#10 + #13#10 +
           'Instale manualmente depois: https://github.com/UB-Mannheim/tesseract/wiki',
           mbInformation, MB_OK);
    Exit;
  end;

  if not FileExists(TempFile) then
  begin
    MsgBox('Download do Tesseract falhou.' + #13#10 +
           'O PDF2LLM funcionará usando EasyOCR como alternativa.',
           mbInformation, MB_OK);
    Exit;
  end;

  // Instala o Tesseract silenciosamente
  WizardForm.StatusLabel.Caption := 'Instalando Tesseract OCR...';
  WizardForm.StatusLabel.Update;
  
  Exec(TempFile, '/S', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  if ResultCode = 0 then
    Log('Tesseract instalado com sucesso.')
  else
    MsgBox('A instalação do Tesseract pode não ter sido bem-sucedida (código: ' + IntToStr(ResultCode) + ').' + #13#10 +
           'O PDF2LLM funcionará usando EasyOCR.', mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsComponentSelected('tesseract') then
      InstallTesseract;
  end;
end;
