@echo off
setlocal enabledelayedexpansion

:: ==========================================
::                НАСТРОЙКИ
:: ==========================================

:: 1. Основные пути
set "ROOT_DIR=C:\valera"
set "PROJECT_SOURCE=%ROOT_DIR%\hmuriy"
set "UNPACKED_DIR=%ROOT_DIR%\unpacked_project"
set "NDK_PATH=C:\android-ndk-r29"

:: Путь к итоговому файлу (рядом с батником)
set "FINAL_BUILD_PATH=%~dp0build.apk"

:: 2. Инструменты (лежат в C:\valera)
set "APKTOOL_JAR=%ROOT_DIR%\apktool.jar"
set "SIGNER_JAR=%ROOT_DIR%\uber-apk-signer.jar"

:: 3. Названия файлов
set "LIB_NAME=libhmuriy.so"
set "UNSIGNED_APK=%ROOT_DIR%\temp_unsigned.apk"
set "TEMP_OUT_DIR=%ROOT_DIR%\release_out"

:: 4. Папка сборки CMake
set "BUILD_DIR=%PROJECT_SOURCE%\build"

:: ==========================================
::                ПРОВЕРКИ
:: ==========================================

if not exist "%NDK_PATH%" (
    echo [ERROR] NDK path not found at: %NDK_PATH%
    pause
    exit /b 1
)
if not exist "%APKTOOL_JAR%" (
    echo [ERROR] Apktool not found at: %APKTOOL_JAR%
    pause
    exit /b 1
)
if not exist "%SIGNER_JAR%" (
    echo [ERROR] Uber-signer not found at: %SIGNER_JAR%
    pause
    exit /b 1
)

:: Проверка наличия Ninja
where ninja >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] 'ninja.exe' not found in PATH. Build might fail if CMake cannot find it.
)

:: Очистка старой папки сборки C++
if exist "%BUILD_DIR%" rd /s /q "%BUILD_DIR%"

:: ==========================================
:: ШАГ 1: Сборка .so библиотеки (C++)
:: ==========================================
echo.
echo [STEP 1/5] Building native library (ARM64)...
echo ------------------------------------------

cmake -B "%BUILD_DIR%" -G "Ninja" ^
    -DCMAKE_TOOLCHAIN_FILE="%NDK_PATH%\build\cmake\android.toolchain.cmake" ^
    -DANDROID_ABI="arm64-v8a" ^
    -DANDROID_PLATFORM=android-21 ^
    -DCMAKE_BUILD_TYPE=Release

if %errorlevel% neq 0 goto :BuildError

cmake --build "%BUILD_DIR%"
if %errorlevel% neq 0 goto :BuildError

:: ==========================================
:: ШАГ 2: Копирование .so в распакованный проект
:: ==========================================
echo.
echo [STEP 2/5] Injecting library into unpacked project...
echo ------------------------------------------

set "TARGET_LIB_DIR=%UNPACKED_DIR%\lib\arm64-v8a"
if not exist "%TARGET_LIB_DIR%" mkdir "%TARGET_LIB_DIR%"

:: Ищем любой .so файл и копируем с правильным именем
set FOUND=0
for /r "%BUILD_DIR%" %%f in (*hmuriy.so) do (
    echo Copying "%%f" to "%TARGET_LIB_DIR%\%LIB_NAME%"
    copy /Y "%%f" "%TARGET_LIB_DIR%\%LIB_NAME%" >nul
    set FOUND=1
)

if %FOUND% equ 0 (
    echo [ERROR] .so library was not found in build artifacts!
    goto :Error
)

:: ==========================================
:: ШАГ 3: Сборка APK через Apktool
:: ==========================================
echo.
echo [STEP 3/5] Rebuilding APK with Apktool...
echo ------------------------------------------

:: Удаляем старый временный файл, если есть
if exist "%UNSIGNED_APK%" del "%UNSIGNED_APK%"

java -jar "%APKTOOL_JAR%" b "%UNPACKED_DIR%" -o "%UNSIGNED_APK%"
if %errorlevel% neq 0 (
    echo [ERROR] Apktool build failed.
    goto :Error
)

:: ==========================================
:: ШАГ 4: Подпись APK и сохранение как build.apk
:: ==========================================
echo.
echo [STEP 4/5] Signing APK and saving as build.apk...
echo ------------------------------------------

:: Очищаем временную папку вывода перед подписью
if exist "%TEMP_OUT_DIR%" rd /s /q "%TEMP_OUT_DIR%"
mkdir "%TEMP_OUT_DIR%"

:: Подписываем во временную папку
java -jar "%SIGNER_JAR%" --apks "%UNSIGNED_APK%" --out "%TEMP_OUT_DIR%"

if %errorlevel% neq 0 (
    echo [ERROR] Signing failed.
    goto :Error
)

:: Находим подписанный файл во временной папке
set "TEMP_SIGNED_APK="
for %%f in ("%TEMP_OUT_DIR%\*.apk") do set "TEMP_SIGNED_APK=%%f"

if not defined TEMP_SIGNED_APK (
    echo [ERROR] Signed APK not found in output directory.
    goto :Error
)

:: Перемещаем и переименовываем файл рядом с батником
echo Moving "%TEMP_SIGNED_APK%" to "%FINAL_BUILD_PATH%"
move /Y "%TEMP_SIGNED_APK%" "%FINAL_BUILD_PATH%" >nul

if not exist "%FINAL_BUILD_PATH%" (
    echo [ERROR] Failed to move file to build.apk
    goto :Error
)

echo [INFO] Final APK ready: %FINAL_BUILD_PATH%

:: ==========================================
:: ШАГ 5: Установка через ADB
:: ==========================================
echo.
echo [STEP 5/5] Installing via ADB...
echo ------------------------------------------

adb install -r "%FINAL_BUILD_PATH%"
if %errorlevel% neq 0 (
    echo [ERROR] ADB Install failed. Check if device is connected and debugging is on.
    goto :Error
)

:: ==========================================
:: ОЧИСТКА МУСОРА
:: ==========================================
echo.
echo [CLEANUP] Removing temporary files...

:: Удаляем папку сборки C++
if exist "%BUILD_DIR%" rd /s /q "%BUILD_DIR%"
:: Удаляем неподписанный APK
if exist "%UNSIGNED_APK%" del "%UNSIGNED_APK%"
:: Удаляем временную папку Uber Signer (так как файл мы забрали)
if exist "%TEMP_OUT_DIR%" rd /s /q "%TEMP_OUT_DIR%"

echo.
echo ==========================================
echo [SUCCESS] Pipeline completed successfully!
echo File location: %FINAL_BUILD_PATH%
echo ==========================================
pause
exit /b 0

:BuildError
echo [ERROR] C++ Build failed.
pause
exit /b 1

:Error
echo.
echo [FAIL] Pipeline stopped due to an error.
pause
exit /b 1