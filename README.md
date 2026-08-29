# 安全衛生委員会サポートAI（ローカル実行用）

`app/main.py` が本体です。`src/` 配下は、元のコードが import していたが未提供だった
6モジュール（`agenda_generator` / `copilot_export` / `slide_generator` / `data_loader` /
`theme_proposer` / `time_comparison`）を、最低限動く形で実装したスタブです。

- 発表デモモード（既定でON）: 定番テーマ3件を即返す
- オフラインモード（デモモードOFF・`OPENAI_API_KEY`未設定時）: ルールベースでテーマ候補を生成
- OpenAIモード: `.env` に `OPENAI_API_KEY` を設定し、`requirements.txt` の末尾コメントにある
  `openai` パッケージを追加インストールすると有効になります（失敗時は自動でオフラインにフォールバック）

会社名・メンバー・履歴データはすべて架空のデモ用データで、初回起動時に `data/` 配下へ自動生成されます。

## 起動方法（Mac：ターミナル不要）

1. このフォルダの中にある **`起動.command`** をダブルクリックしてください
2. 初回だけ、自動でセットアップ（仮想環境の作成・ライブラリのインストール）が走ります（数分かかります）
3. セットアップ後、自動でブラウザが開きます

「開発元が未確認のため開けません」と出た場合は、Finderで `起動.command` を **右クリック（controlキー+クリック）→「開く」** を選び、表示されたダイアログで再度「開く」を押してください（初回のみ必要な操作です）。

ダブルクリックすると黒い画面（ターミナル）が一瞬開きますが、これはアプリを裏で動かすためのウィンドウです。特に操作する必要はありません。**アプリを終了するときは、このウィンドウを閉じてください。**

2回目以降の起動も同じく `起動.command` をダブルクリックするだけです（ライブラリが既にある場合はすぐに立ち上がります）。

### コマンドラインから起動したい場合（任意）

```bash
cd anzen-eisei-committee-app
python3 -m venv .venv
source .venv/bin/activate        # Windowsは .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
```

自動でブラウザが開きます。開かない場合は表示された `http://localhost:8501` にアクセスしてください。
（このURLはあなたのPC上でのみ有効です）

## ディレクトリ構成

```
anzen-eisei-committee-app/
├── 起動.command          # ダブルクリックで起動するランチャー（Mac用）
├── app/
│   └── main.py          # Streamlitアプリ本体（いただいたコードそのまま）
├── src/
│   ├── agenda_generator.py
│   ├── copilot_export.py
│   ├── slide_generator.py
│   ├── data_loader.py
│   ├── theme_proposer.py
│   └── time_comparison.py
├── data/                 # 初回起動時に自動生成（履歴CSV・会社情報など）
├── .venv/                # 初回起動時に自動生成（Python仮想環境）
├── requirements.txt
├── .env.example
└── README.md
```

## 既知の制約（スタブ実装について）

- `theme_proposer` のOpenAI連携は簡易実装です。本番相当のプロンプト設計・エラーハンドリングは
  元の実装に合わせて調整してください。
- `python-docx` / `python-pptx` が未インストールの場合、Word/スライド出力はプレーンテキストの
  フォールバックになります（`requirements.txt`通りインストールすれば正常に生成されます）。
