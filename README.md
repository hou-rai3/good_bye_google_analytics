# 【Ubuntu 24.04】Docker Composeで構築する自作ユーザー行動監視サーバー（愛称：グッバイ Google Analytics(^_^)/）

## 1. 課題概要

### 目的

本プロジェクト「good_bye_google_analytics」は、Google Analytics等のサードパーティ製ツールに依存せず、プライバシーに配慮した形でWebサイト上のユーザー行動（クリックイベント等）を記録・可視化するサーバーを構築することを目的とする。
既存の解析ツールは多機能だが、データが外部に送信される懸念がある。本システムは自社（自分）管理下のサーバーで完結し、Docker Composeを用いることで、手順書通りに作業すれば誰でも再現可能な環境構築を目指す。

### 完成条件

1. Ubuntu 24.04上で、コマンド一つでWeb・App・DBのサーバー群が一括起動すること。
2. ブラウザから管理画面（`/admin`）にアクセスし、ログが閲覧できること。
3. 外部サイト（またはテスト用ページ）のJavaScriptから、非同期通信でログを送信し、DBに保存されること。

### 採用した発展要素

本構築では、課題要件の以下の発展的要素を取り入れている。

* **例 B：Docker Compose による Web＋DB の 2 コンテナ構成**
実際には Nginx (Web)、Flask (App)、MariaDB (DB) の3層アーキテクチャを採用している。
* **例 A：逆プロキシ（Nginx）によるCORS制御**
外部ドメインからのビーコン（ログ送信）を受け付けるためのオリジン許可設定を実装している。

---

## 2. 前提条件

構築作業を行う環境および前提は以下の通りである。

* **対象OS:** Ubuntu 24.04 LTS (Noble Numbat)
* **実行環境:** ローカル物理マシン または 仮想マシン
* **権限:** `sudo` 権限を持つユーザーであること
* **ネットワーク:** インターネット接続（Dockerイメージ取得のため）、HTTP(80番ポート)が開放されていること
* **前提知識:** Linuxの基本コマンド操作、基本的なTCP/IPの理解

---

## 3. システム構成図とディレクトリ設計

### 全体構成

Nginxをフロントに置き、静的ファイル配信とAPIへのリバースプロキシを行う。データはMariaDBに永続化する。

```mermaid
graph LR
    User[ユーザー/Client] -- HTTP:80 --> Nginx[Web: Nginx]
    Nginx -- /api/ --> Flask[App: Flask]
    Nginx -- static files --> Static[HTML/JS]
    Flask -- TCP:3306 --> DB[(DB: MariaDB)]

```

### ディレクトリ構成

GitHubリポジトリよりクローンする構成は以下の通りである。環境変数を管理するファイルは使用せず、設定ファイル内に直接記述するシンプルな構成としている。

```text
good_bye_google_analytics/
├── README.md                # 本ドキュメント
└── simple-tracker/
    ├── docker-compose.yml   # コンテナ構成定義
    ├── backend/
    │   ├── app.py           # Flaskアプリケーション本体
    │   ├── Dockerfile       # Python環境定義
    │   └── requirements.txt # Python依存ライブラリ
    ├── nginx/
    │   └── default.conf     # Nginx設定（リバースプロキシ・CORS）
    └── html/
        ├── tracker.js       # ログ送信クライアントスクリプト
        └── test.html        # 動作確認用ページ

```

---

## 4. 事前準備

Ubuntu環境を最新化し、DockerおよびDocker Composeを導入する。

### 4.1 パッケージの更新

まずシステムを最新の状態にする。

```bash
sudo apt update && sudo apt upgrade -y

```

### 4.2 Docker / Docker Compose のインストール

```bash
# 必要なパッケージのインストール
sudo apt install -y ca-certificates curl gnupg lsb-release

# Docker公式GPG鍵の追加
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# リポジトリのセットアップ
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker Engineのインストール
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

```

### 4.3 動作確認

以下のコマンドでバージョンが表示されれば準備完了である。

```bash
docker --version
docker compose version

```

---

## 5. 構築手順（再現手順）

本システムはGitリポジトリおよびDocker Composeを利用することで、複雑な手順を省略し、再現性を高めている。

### 手順1: リポジトリのクローン

ソースコード一式をローカル環境にダウンロードし、作業ディレクトリへ移動する。

```bash
cd ~
git clone https://github.com/hou-rai3/good_bye_google_analytics.git
cd good_bye_google_analytics/simple-tracker

```

### 手順2: コンテナのビルドと起動

Docker Composeを使用して、イメージのビルドとコンテナの起動を行う。

```bash
# バックグラウンド(-d)でビルド(--build)して起動
sudo docker compose up -d --build

```

### 手順3: 起動状態の確認

全てのコンテナが `Up` 状態であることを確認する。

```bash
sudo docker compose ps

```

実行結果例：

```text
NAME                           STATUS          PORTS
simple-tracker-db-1            Up (healthy)    3306/tcp
simple-tracker-backend-1       Up              5000/tcp
simple-tracker-nginx-1         Up              0.0.0.0:80->80/tcp

```

---

## 6. 動作確認と検証

サーバーが正常に機能しているか、以下の手順で検証を行う。

### 検証1: テストページへのアクセス

ブラウザを開き、以下のURLへアクセスする。

* URL: `http://localhost/test.html` (またはサーバーのIPアドレス)

画面上のボタンをクリックし、「ログを送信しました」などのアラートや表示が出れば、JavaScriptからサーバーへの通信が成功している。

*(ここに `test.html` のブラウザスクリーンショットを配置)*

### 検証2: ログデータの確認（管理画面）

ログがデータベースに保存されているか確認する。

* URL: `http://localhost/admin`

クリックした日時、User-Agent、IPアドレス等の情報がテーブル形式で表示されていれば、Web→App→DBの連携は正常である。

*(ここに `/admin` 画面のスクリーンショットを配置)*

### 検証3: DBコンテナの永続化確認

一度コンテナを削除してもデータが残るか検証する。

```bash
# コンテナを停止・削除
sudo docker compose down

# 再度起動
sudo docker compose up -d

```

ブラウザで再度 `/admin` にアクセスし、先ほどのデータが残っていれば永続化の確認は完了である。

---

## 7. 設定ファイル解説（主要部分の完全版）

再現性と理解度を示すため、主要な設定ファイルの完全版を掲載する。今回は環境変数ファイルを使用せず、直接設定を記述している。

### docker-compose.yml

各コンテナの依存関係とネットワーク定義。データベースのパスワード等はここで指定している。

```yaml
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
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./html:/usr/share/nginx/html
    depends_on:
      - backend
    networks:
      - tracker-net

volumes:
  db_data:

networks:
  tracker-net:
    driver: bridge

```

### nginx/default.conf

リバースプロキシとCORS（Cross-Origin Resource Sharing）の設定。

```nginx
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

```

---

## 8. トラブルシューティング

よくあるエラーとその対処法を記す。

### Case 1: ポート80が既に使用されている

* **エラー:** `Bind for 0.0.0.0:80 failed: port is already allocated`
* **原因:** Ubuntu標準のApache等が既に起動している。
* **対処:** `sudo systemctl stop apache2` で停止するか、`docker-compose.yml` のNginxポート設定を `"8080:80"` 等に変更する。

### Case 2: データベース接続エラー

* **エラー:** Backendコンテナのログ（`sudo docker compose logs backend`）に `Can't connect to MySQL server` と出る。
* **原因:** DBコンテナの起動完了前にAppコンテナが接続しようとした。
* **対処:** 本構成では `restart: always` を設定しているため自動で再試行されるが、手動で `sudo docker compose restart backend` を実行すると解決する。

---

## 9. セキュリティと今後の展望

### セキュリティ配慮

1. **最小権限の原則:** DB接続にはrootユーザーではなく、専用の一般ユーザー（`tracker_user`）を使用している。
2. **内部ネットワークの閉域化:** DB（3306ポート）やBackend（5000ポート）はホストに直接公開せず、Dockerの内部ネットワーク（`tracker-net`）でのみ通信させている。

### 今後の展望

現在は構成の簡略化のため `docker-compose.yml` に認証情報を直接記述しているが、実運用においては `.env` ファイルを導入して認証情報を分離し、Git管理から除外する手法への移行が推奨される。また、NginxにSSL証明書（Let's Encrypt等）を追加してHTTPS化を行うことで、よりセキュアな通信網を構築可能である。

### 参考文献

* Docker Compose 公式ドキュメント: [https://docs.docker.com/compose/](https://docs.docker.com/compose/)
* Flask 公式ドキュメント: [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
* Nginx リバースプロキシ設定: [https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
