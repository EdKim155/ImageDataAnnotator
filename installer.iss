; Скрипт для создания установщика Image Data Annotator с помощью Inno Setup
; Для компиляции установщика:
; 1. Установите Inno Setup: https://jrsoftware.org/isdl.php
; 2. Откройте этот файл в Inno Setup Compiler
; 3. Нажмите Build -> Compile

#define MyAppName "Image Data Annotator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Image Data Annotator"
#define MyAppExeName "ImageDataAnnotator.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".ida"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; Основные настройки приложения
AppId={{A3B2C1D4-E5F6-4A5B-8C7D-9E0F1A2B3C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Папка для вывода установщика
OutputDir=dist\installer
OutputBaseFilename=ImageDataAnnotator-Setup-v{#MyAppVersion}
; Иконка установщика
SetupIconFile=resources\icon.ico
; Сжатие
Compression=lzma2
SolidCompression=yes
; Windows Vista и выше
MinVersion=6.1
; Архитектура
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Привилегии
PrivilegesRequired=lowest
; Языки
ShowLanguageDialog=auto

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Копируем все файлы из dist\ImageDataAnnotator
Source: "dist\ImageDataAnnotator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Копируем иконку
Source: "resources\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Ярлык в меню Пуск
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
; Ярлык для удаления
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Ярлык на рабочем столе
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon
; Ярлык в панели быстрого запуска
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Запустить приложение после установки
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Проверка наличия других версий приложения
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
end;

[Messages]
; Русские сообщения
russian.WelcomeLabel2=Программа установит [name/ver] на Ваш компьютер.%n%nЭта программа позволяет автоматически добавлять данные из Excel на изображения.
russian.FinishedLabel=Установка [name] завершена.%n%nВы можете запустить приложение, выбрав установленные значки.
