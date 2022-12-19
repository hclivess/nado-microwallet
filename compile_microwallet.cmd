rmdir /s /q microwallet.build
rmdir /s /q microwallet.dist
python -m nuitka microwallet.py --msvc=latest --standalone --windows-icon-from-ico=graphics\icon.ico --enable-plugin=tk-inter --include-package-data=customtkinter
xcopy /e /i /y sources\customtkinter microwallet.dist\customtkinter
xcopy /e /i /y %userprofile%\nado\peers microwallet.dist\peers
"C:\Program Files (x86)\Inno Setup 6\iscc" /q "setup.iss"
pause