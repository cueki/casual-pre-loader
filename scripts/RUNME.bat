if exist ".tmp_update" (
    robocopy ".tmp_update" . /E /MOVE
    rmdir ".tmp_update"
    ./RUNME.bat
)

cd casual-preloader
python.exe pip.pyz install -q -r requirements.txt
python.exe main.py
