@echo off
REM 仮想環境がなければ作成
if not exist venv (
    python -m venv venv
)

REM 仮想環境をアクティブ化
call venv\Scripts\activate

REM ライブラリをインストール
pip install --upgrade pip
pip install -r requirements.txt

REM exeを起動
py mosaic_app.py

REM 仮想環境を終了（必要なら）
REM deactivate 