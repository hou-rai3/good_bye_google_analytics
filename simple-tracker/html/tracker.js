// 即時関数でスコープを汚染しない
(function() {
    console.log("Tracker: Initializing...");

    // 1. 設定取得 (自分のURLからパラメータをパース)
    const scripts = document.getElementsByTagName('script');
    const myScript = scripts[scripts.length - 1];
    const urlParams = new URLSearchParams(myScript.src.split('?')[1]);
    const siteId = urlParams.get('site_id') || 'unknown_site';
    
    // APIのエンドポイント（重要: これが監視サーバーのURL）
    // ※GitHub Pagesで使う場合は、ここをグローバルIPやngrokのURLにする必要あり
    // ローカルテスト用:
    const API_ENDPOINT = 'http://localhost:8080/api/track'; 

    // 2. ユーザーID管理
    let userId = localStorage.getItem('st_uid');
    if (!userId) {
        userId = 'u_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('st_uid', userId);
    }

    // 3. クリック監視
    document.addEventListener('click', function(e) {
        // data-track-id属性を持つ要素、またはその親要素を探す
        const target = e.target.closest('[data-track-id]');
        
        if (target) {
            const elementId = target.getAttribute('data-track-id');
            console.log(`Tracker: Clicked ${elementId}`);

            // ログ送信 (sendBeaconは画面遷移時も送信されやすい)
            const data = JSON.stringify({
                site_id: siteId,
                user_id: userId,
                element_id: elementId
            });

            if (navigator.sendBeacon) {
                navigator.sendBeacon(API_ENDPOINT, new Blob([data], {type: 'application/json'}));
            } else {
                fetch(API_ENDPOINT, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: data
                });
            }
        }
    });
})();
