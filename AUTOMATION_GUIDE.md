# TOKYO CLUB EVENTS RADAR — 自動更新システム運用ガイド

本ポータルは、各クラブの公式スケジュールやフライヤー情報の更新を自動で検知・集約し、常に最新のイベント情報を公開できる**「サーバーレス自動巡回＆リアルタイム配信システム」**として設計されています。

---

## 1. システム構成・アーキテクチャ

```
[各クラブ公式HP / スケジュール]
       │
       ▼ (毎朝06:00 JST / 手動トリガー)
[自動クローラーエンジン (crawler.py)]
  - 日程・出演者・ジャンル・料金の正規化
  - 過去イベント（終了済）の自動判定・アーカイブ化
  - 公式フライヤーの検証・店舗ロゴフォールバック
       │
       ▼ (データ出力)
[data/clubs_events_data.json]
       │
       ├─► [GitHub Actions (.github/workflows/update_events.yml)]
       │      └─► GitHub Pages / Vercel へ自動デプロイ（完全無料）
       │
       ▼
[Webポータル (index.html)]
  - ページを開いた瞬間に fetch(`data/clubs_events_data.json`) を実行
  - 画面上部に「🟢 最新自動同期: YYYY/MM/DD HH:mm JST」と [🔄 再取得] ボタンを表示
  - ローカル環境(file://)や通信障害時も埋め込みデータで100%安全に動作
```

---

## 2. 導入済みコンポーネント一覧

1. **`crawler.py`（自動巡回・データ更新エンジン）**
   - 全31クラブの最新イベント情報、フライヤー、開催終了フラグ（現在日時より前か判定）を自動更新し、`data/clubs_events_data.json` を生成します。
2. **`data/clubs_events_data.json`（最新イベントデータベース）**
   - 最終更新日時（`last_updated_at`）、全クラブ、全イベント、フライヤーURLが格納された配信元データ。
3. **`.github/workflows/update_events.yml`（GitHub Actions 自動実行パイプライン）**
   - 毎日午前6:00（JST）に自動で起動し、クローラーを実行して最新データをリポジトリにコミット＆GitHub Pagesに自動デプロイします。
4. **`index.html`（動的同期対応フロントエンド）**
   - ハードコード不要で、起動時に最新の `clubs_events_data.json` を非同期取得してカレンダーやイベントカードを再描画します。

---

## 3. 完全無料・サーバー代0円で自動運用を開始する手順

### Step 1: GitHubにリポジトリを登録
本ディレクトリの全ファイルを、ご自身のGitHubリポジトリ（Public推奨）にプッシュします。

```bash
git init
git add .
git commit -m "Initial commit for Tokyo Club Radar"
git branch -M main
git remote add origin https://github.com/<YOUR_USER>/<YOUR_REPO>.git
git push -u origin main
```

### Step 2: GitHub Pages の設定
1. GitHubのリポジトリ画面で **「Settings」** タブを開きます。
2. 左メニューの **「Pages」** をクリックします。
3. **「Build and deployment」** の **「Source」** を **「GitHub Actions」** に設定します。

### Step 3: 自動更新の稼働
- **自動巡回**: これで毎朝日本時間 06:00 に自動的にクローラーが巡回し、最新のイベントデータがWeb上に自動反映されます。
- **今すぐ手動実行したい場合**:
  GitHubの **「Actions」** タブ → **「Automated Club Events Crawler & Deploy」** を選択し、**「Run workflow」** ボタンを押すだけで、いつでも即座に最新化されます。

---

## 4. ローカル環境での手動同期実行

開発中やテスト時にPC上で手動更新したい場合は、ターミナルで以下のコマンドを実行します。

```bash
# 1. クローラーを実行して最新イベントデータを取得・更新
python3 crawler.py

# 2. 静的配信用のindex.htmlを再ビルド
python3 build_clean_index.py
```
