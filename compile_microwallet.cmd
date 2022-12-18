rmdir /s /q nado.build
rmdir /s /q nado.dist
python -m nuitka microwallet.py --follow-imports --include-data-files="C:/Program Files/Python310/Lib/site-packages/customtkinter/*.*=customtkinter/" --windows-icon-from-ico=graphics\icon.ico --enable-plugin=tk-inter
xcopy /e /i /y sources\customtkinter microwallet.dist\customtkinter
"C:\Program Files (x86)\Inno Setup 6\iscc" /q "setup.iss"
pause
