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

[Types]
Name: "full"; Description: "Instalação completa (com Tesseract OCR)"
Name: "compact"; Description: "Instalação mínima (sem Tesseract)"
Name: "custom"; Description: "Personalizada"; Flags: iscustom

[Components]
Name: "main"; Description: "PDF2LLM - Aplicação principal"; Types: full compact custom; Flags: fixed
Name: "tesseract"; Description: "Tesseract OCR (recomendado - melhora OCR em PDFs escaneados)"; Types: full

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
  
  // PowerShell busca a URL mais recente do Tesseract via GitHub API
  // e faz o download automaticamente (funciona mesmo quando mudam de versão)
  DownloadCmd := 'powershell -ExecutionPolicy Bypass -Command "& { ' +
    '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ' +
    'try { ' +
    '$rel = Invoke-RestMethod ''https://api.github.com/repos/UB-Mannheim/tesseract/releases/latest''; ' +
    '$asset = $rel.assets | Where-Object { $_.name -like ''*w64-setup*'' } | Select-Object -First 1; ' +
    'if ($asset) { Invoke-WebRequest -Uri $asset.browser_download_url -OutFile ''' + TempFile + ''' } ' +
    'else { exit 1 } ' +
    '} catch { exit 1 } ' +
    '}"';
  
  WizardForm.StatusLabel.Caption := 'Baixando Tesseract OCR (última versão)...';
  WizardForm.StatusLabel.Update;
  
  Exec('cmd.exe', '/C ' + DownloadCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if (ResultCode <> 0) or (not FileExists(TempFile)) then
  begin
    MsgBox('Não foi possível baixar o Tesseract OCR.' + #13#10 +
           'O PDF2LLM funcionará normalmente usando EasyOCR como alternativa.' + #13#10 + #13#10 +
           'Para instalar o Tesseract manualmente:' + #13#10 +
           'https://github.com/UB-Mannheim/tesseract/wiki',
           mbInformation, MB_OK);
    Exit;
  end;

  // Instala o Tesseract (pede elevação de admin pois o Tesseract exige)
  WizardForm.StatusLabel.Caption := 'Instalando Tesseract OCR (pode pedir permissão de administrador)...';
  WizardForm.StatusLabel.Update;
  
  if not ShellExec('runas', TempFile, '/S', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('A instalação do Tesseract foi cancelada (permissão negada).' + #13#10 +
           'O PDF2LLM funcionará usando EasyOCR como alternativa.' + #13#10 + #13#10 +
           'Para instalar depois: https://github.com/UB-Mannheim/tesseract/wiki',
           mbInformation, MB_OK);
    Exit;
  end;
  
  if ResultCode = 0 then
    Log('Tesseract instalado com sucesso.')
  else
    MsgBox('A instalação do Tesseract pode não ter sido concluída (código: ' + IntToStr(ResultCode) + ').' + #13#10 +
           'O PDF2LLM funcionará usando EasyOCR como alternativa.', mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsComponentSelected('tesseract') then
      InstallTesseract;
  end;
end;
