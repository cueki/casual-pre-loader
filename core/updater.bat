  @echo off
  if "%~3"=="" (
      echo Usage: updater.bat ^<zip_path^> ^<install_dir^> ^<main_process_pid^>
      exit /b 1
  )

  set "zip_path=%~1"
  set "install_dir=%~2"
  set "main_pid=%~3"

  echo Terminating main process (PID: %main_pid%)...
  taskkill /PID %main_pid% /F >nul 2>&1
  if %errorlevel%==0 (
      echo Main process terminated
  ) else (
      echo Warning: Could not terminate main process
  )

  echo Waiting 2 seconds...
  timeout /t 2 /nobreak >nul

  echo Extracting update to %install_dir%...
  tar -xf "%zip_path%" -C "%install_dir%"

  if %errorlevel%==0 (
      echo Update extracted successfully!

      del "%zip_path%" >nul 2>&1
      if %errorlevel%==0 echo Cleaned up zip file

      echo Restarting application...
      cd /d "%install_dir%\casual-preloader"
      python.exe main.py
  ) else (
      echo ERROR: Failed to extract update (exit code: %errorlevel%)
      echo Press any key to exit...
      pause >nul
  )
