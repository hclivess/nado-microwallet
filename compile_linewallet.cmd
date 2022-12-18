rmdir /s /q linewallet.build
rmdir /s /q linewallet.dist
python -m nuitka linewallet.py --onefile --windows-icon-from-ico=graphics\icon.ico
pause