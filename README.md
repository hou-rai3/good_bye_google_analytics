# 【Ubuntu 24.04】Docker Composeで構築する自作ユーザー行動監視サーバー（愛称：グッバイ Google Analytics(^_^)/）

## 1. 課題概要

### 目的
本プロジェクト「Simple-Click-Visualizer」は、Google Analytics等のサードパーティ製ツールに依存せず、プライバシーに配慮した形でWebサイト上のユーザー行動（クリックイベント等）を記録・可視化するサーバーを構築することを目的とする。既存の解析ツールは多機能だが、データが外部に送信される懸念がある。本システムは自社（自分）管理下のサーバーで完結し、Docker Composeを用いることで、手順書通りに作業すれば誰でも再現可能な環境構築を目指す。

### 完成条件
1. Ubuntu 24.04上で、コマンド一つでWeb・App・DBのサーバー群が一括起動すること。
2. ブラウザから管理画面（`/admin`）にアクセスし、ログが閲覧できること。
3. 外部サイト（またはテスト用ページ）のJavaScriptから、非同期通信でログを送信し、DBに保存されること。

### 採用した発展要素
本構築では、授業内容を基盤として課題要件の以下の発展的要素を取り入れている。
* **例 B：Docker Compose による Web＋DB の 2 コンテナ構成**
  実際には Nginx (Web)、Flask (App)、MariaDB (DB) の3層アーキテクチャを採用している。
* **例 Aの一部：逆プロキシ（Nginx）によるCORS制御**
  外部ドメインからのビーコン（ログ送信）を受け付けるためのオリジン許可設定を実装している。

---

## 2. 前提条件

構築作業を行う環境および前提は以下の通りである。

* **対象OS:** Ubuntu 24.04 LTS (Noble Numbat)
* **実行環境:** ローカル仮想マシン（VMware 等） または 学内クラウドVM
* **利用ツール・パッケージ管理手段:** `apt` (OSパッケージ管理)、`git`、`docker`、`docker compose`
* **ネットワーク条件:** * インターネット接続あり（パッケージおよびDockerイメージ取得のため）
  * 固定IPまたはローカルIPアクセス可能、HTTP(TCP 80番ポート)が開放されていること
* **操作権限:** `sudo` 権限を持つ一般ユーザー（本手順書ではユーザー名を `ubuntu` と想定）

---

## 3. システム構成図とポート設計

### ポート設計と通信経路
外部からのアクセスはフロントエンドのNginxがすべて受け付け、リクエストパスに応じて内部のコンテナへ処理を振り分ける。データベースは内部ネットワークに完全に隔離する。

* **外部 -> Nginx:** TCP 80 (HTTP) で受付。静的ファイルを配信する。
* **Nginx -> Flask (Backend):** リクエストパスが `/api/` または `/admin` の場合、Docker内部ネットワーク経由で Flaskコンテナの TCP 5000 へリバースプロキシする。
* **Flask -> MariaDB (DB):** ログの保存・取得のため、Docker内部ネットワーク経由で MariaDBコンテナの TCP 3306 へ通信する。

### 全体構成図
```mermaid
graph LR
    User[ユーザー/Client] -- HTTP:80 --> Nginx[Web: Nginx]
    Nginx -- /api/ 及び /admin --> Flask[App: Flask:5000]
    Nginx -- 静的ファイル --> Static[HTML/JS]
    Flask -- TCP:3306 --> DB[(DB: MariaDB)]
ディレクトリ構成
GitHubリポジトリよりクローンする構成は以下の通りである。

Plaintext

good_bye_google_analytics/
├── README.md                
└── simple-tracker/
    ├── docker-compose.yml   
    ├── backend/
    │   ├── app.py           
    │   ├── Dockerfile       
    │   └── requirements.txt 
    ├── nginx/
    │   └── default.conf     
    └── html/
        ├── tracker.js       
        └── test.html        
4. 事前準備
Ubuntu環境を最新化し、DockerおよびDocker Composeを導入する。

4.1 パッケージの更新
Bash

# パッケージリストを更新し、インストール済みパッケージをアップグレードする
sudo apt update && sudo apt upgrade -y
4.2 Docker / Docker Compose のインストール
Bash

# HTTPS経由でリポジトリを使用するための必須パッケージをインストール
sudo apt install -y ca-certificates curl gnupg lsb-release

# Docker公式のGPG鍵を保存するディレクトリを作成
sudo mkdir -p /etc/apt/keyrings

# Docker公式のGPG鍵をダウンロードして配置
curl -fsSL [https://download.docker.com/linux/ubuntu/gpg](https://download.docker.com/linux/ubuntu/gpg) | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Dockerの公式リポジトリをAPTソースリストに追加
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] [https://download.docker.com/linux/ubuntu](https://download.docker.com/linux/ubuntu) $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 追加したリポジトリのパッケージリストを更新し、Docker本体とプラグインをインストール
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
4.3 インストール完了の確認
以下のコマンドを実行し、バージョン情報が出力されることを確認する。

Bash

docker --version
docker compose version
(ここに上記コマンドを実行し、バージョンが表示されているターミナルのスクリーンショットを追加)

5. 構築手順（再現手順）
GitリポジトリおよびDocker Composeを利用することで、構築の再現性を高めている。

手順1: リポジトリのクローン
ソースコード一式をダウンロードし、作業ディレクトリへ移動する。

Bash

# ホームディレクトリへ移動
cd ~
# GitHubからリポジトリをクローン
git clone [https://github.com/hou-rai3/good_bye_google_analytics.git](https://github.com/hou-rai3/good_bye_google_analytics.git)
# 作業用ディレクトリへ移動
cd good_bye_google_analytics/simple-tracker
手順2: コンテナのビルドと起動
Docker Composeを使用して、設定ファイルに基づきイメージのビルドとコンテナの起動を行う。

Bash

# バックグラウンド(-d)でイメージをビルド(--build)し、全コンテナを起動する
sudo docker compose up -d --build
6. 設定ファイル解説（主要部分の完全版）
設定ファイルの完全版を記載する。本構成ではシークレット情報はダミー値に置き換えて記載している。

6.1 docker-compose.yml
各コンテナの依存関係とネットワーク定義。データベースの初期設定（ダミーパスワード）もここで指定する。

保存パス: ~/good_bye_google_analytics/simple-tracker/docker-compose.yml

所有権・権限: ubuntu:ubuntu (644)

YAML

version: '3.8'

services:
  db:
    image: mariadb:10.6
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: root_password_here
      MYSQL_DATABASE: tracker_db
      MYSQL_USER: tracker_user
      MYSQL_PASSWORD: user_password_here
    volumes:
      - db_data:/var/lib/mysql
    networks:
      - tracker-net

  backend:
    build: ./backend
    restart: always
    environment:
      DB_HOST: db
      DB_USER: tracker_user
      DB_PASSWORD: user_password_here
      DB_NAME: tracker_db
    depends_on:
      - db
    networks:
      - tracker-net

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./html:/usr/share/nginx/html:ro
    depends_on:
      - backend
    networks:
      - tracker-net

volumes:
  db_data:

networks:
  tracker-net:
    driver: bridge
6.2 Nginx 設定ファイル (default.conf)
リバースプロキシとCORS（Cross-Origin Resource Sharing）の制御設定。

保存パス: ~/good_bye_google_analytics/simple-tracker/nginx/default.conf

所有権・権限: ubuntu:ubuntu (644)

Nginx

server {
    listen 80;
    server_name localhost;

    # 静的ファイルの配信
    location / {
        root /usr/share/nginx/html;
        index test.html;
    }

    # APIへのリバースプロキシ
    location /api/ {
        # CORS設定：異なるドメインからのJSリクエストを許可
        add_header 'Access-Control-Allow-Origin' '*';
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS';
        add_header 'Access-Control-Allow-Headers' 'Content-Type';

        proxy_pass http://backend:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 管理画面へのリバースプロキシ
    location /admin {
        proxy_pass http://backend:5000/admin;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
7. 動作確認と検証
構築したシステムが正常に動作しているか、多角的に検証する。

7.1 コンテナの稼働ステータス確認
全てのコンテナが Up 状態であること、およびNginxのポート(80)が開放されているか確認する。

Bash

sudo docker compose ps
(ここに docker compose ps の結果が表示されているターミナルのスクリーンショットを追加)

7.2 コマンドラインからのAPI疎通確認（ヘルスチェック）
Nginxを経由してBackendのAPIへ正しくルーティングされ、DBへの書き込み処理が走るかテストする。

Bash

curl -X POST -H "Content-Type: application/json" -d '{"action": "curl_test_event"}' http://localhost/api/track
※期待される出力例：{"message":"Action Logged","status":"success"}

(ここに curl コマンドを実行し、successメッセージが返ってきたターミナルのスクリーンショットを追加)

7.3 バックエンドログの確認
APIがリクエストを正しく処理しているか、コンテナの標準出力を確認する。

Bash

sudo docker compose logs backend
(ここに docker compose logs backend を実行し、POSTリクエストの処理履歴が出力されているターミナルのスクリーンショットを追加)

7.4 ブラウザからの動作確認とログ閲覧
ブラウザで http://<サーバーのIPアドレス>/test.html にアクセスする。

画面上のボタンをクリックし、「ログを送信しました」のアラートが出ることを確認する。

ブラウザで http://<サーバーのIPアドレス>/admin にアクセスする。

先ほどの curl_test_event や、ボタンクリックの履歴がテーブル形式で表示されていれば成功である。

(ここにブラウザで /admin 画面を開き、ログ一覧が表示されているスクリーンショットを追加)

8. トラブルシューティング
事象1: ポート80が既に使用されている（ポート競合）

エラー: Bind for 0.0.0.0:80 failed: port is already allocated

原因: Ubuntu標準のApache2等が既に80番ポートを占有している。

対処: sudo systemctl stop apache2 および sudo systemctl disable apache2 でApacheを停止するか、docker-compose.yml のNginxポート設定を "8080:80" 等に変更する。

事象2: Backendがデータベースに接続できない

エラー: Backendコンテナのログに Can't connect to MySQL server と出る。

原因: DBコンテナの初期化が完了する前にAppコンテナが接続しようとした。

対処: 本構成では restart: always を設定しているため自動で再試行され復旧する。手動で即時解決する場合は sudo docker compose restart backend を実行する。

9. セキュリティとまとめ
最小権限の原則: DB接続にはrootユーザーではなく、専用の一般ユーザー（tracker_user）を使用している。

ネットワークの閉域化: DB（3306ポート）やBackend（5000ポート）はホストへ直接公開せず、Dockerの内部ネットワーク（tracker-net）でのみ通信させ、外部からの直接攻撃を防いでいる。

秘密情報の扱い: 本手順書上では root_password_here などのダミー値を記載している。

今後の展望
NginxにSSL証明書（Let's Encrypt等）を追加してHTTPS化を行うことで、よりセキュアな通信網の構築が可能である。

10. 参考資料・特記事項
Docker Compose 公式ドキュメント: https://docs.docker.com/compose/

Flask 公式ドキュメント: https://flask.palletsprojects.com/

Nginx リバースプロキシ設定: https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/

【生成AIの利用について】
本ドキュメントの作成および手順の構成推敲にあたり、LLM（Google Gemini）を活用した。出力されたコマンド、設定ファイルの内容、および検証手順はすべてローカル環境にて動作検証を実施し、事実関係と課題要件との整合性を確認した上で提出している。


【注意点・例外】
* `*(ここに...のスクリーンショットを追加)*` と記載されている全5箇所に、自身の環境で実行した画像を挿入すること。Markdownでの画像挿入方法は `![説明文](./画像の相対パス.png)` である。
* 提出時のファイル名は「3I-出席番号-手順書.md」とすること。

【出典】
* ユーザーから提示された課題の評価基準および必須構成

【確実性: 高】
