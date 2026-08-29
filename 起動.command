#!/bin/bash
# 安全衛生委員会サポートAI - 起動ランチャー（Mac用）
# Finderでこのファイルをダブルクリックすると、自動でセットアップ＆起動します。

# このファイル自身があるフォルダに移動
cd "$(dirname "$0")" || exit 1

echo "=========================================="
echo " 安全衛生委員会サポートAI を起動します"
echo "=========================================="
echo ""

# python3 の存在チェック
if ! command -v python3 >/dev/null 2>&1; then
  echo "エラー：python3 が見つかりません。"
  echo "https://www.python.org/downloads/ からPython 3をインストールしてから、"
  echo "もう一度このファイルをダブルクリックしてください。"
  echo ""
  read -r -p "Enterキーを押すとこのウィンドウを閉じます..."
  exit 1
fi

# 初回のみ仮想環境を作成
if [ ! -d ".venv" ]; then
  echo "初回セットアップ中です。数分かかる場合があります…"
  python3 -m venv .venv
  if [ $? -ne 0 ]; then
    echo "エラー：仮想環境の作成に失敗しました。"
    read -r -p "Enterキーを押すとこのウィンドウを閉じます..."
    exit 1
  fi
fi

source .venv/bin/activate

# 必要なライブラリを確認・インストール（2回目以降は一瞬で終わります）
echo "必要なライブラリを確認しています…"
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
  echo "エラー：ライブラリのインストールに失敗しました。インターネット接続を確認してください。"
  read -r -p "Enterキーを押すとこのウィンドウを閉じます..."
  exit 1
fi

echo ""
echo "起動します。数秒後にブラウザが自動で開きます。"
echo "アプリを終了するときは、このウィンドウを閉じてください。"
echo ""

streamlit run app/main.py

echo ""
echo "アプリを終了しました。"
read -r -p "Enterキーを押すとこのウィンドウを閉じます..."
