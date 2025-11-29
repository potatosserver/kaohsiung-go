// Service Worker Version
// 更新版本號以觸發 activate 事件清除舊快取
const CACHE_NAME = 'kh-transport-v2';

// 這些資源會被安裝時預先快取
const STATIC_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './icons/icon.ico',
    
    // Leaflet 核心與聚合套件
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.css',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.Default.css',
    'https://unpkg.com/leaflet.markercluster/dist/leaflet.markercluster.js',
    
    // UI 樣式與字型
    'https://cdn.tailwindcss.com',
    'https://fonts.googleapis.com/icon?family=Material+Icons+Outlined|Material+Icons+Round',
    'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap'
];

// 安裝階段：預先下載靜態資源
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('SW: Pre-caching offline assets');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting(); // 強制讓新的 SW 立刻進入 active 狀態
});

// 啟用階段：清除舊版本的快取
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => {
                    console.log('SW: Removing old cache', key);
                    return caches.delete(key);
                })
            );
        })
    );
    self.clients.claim(); // 讓 SW 立刻控制所有頁面
});

// 攔截請求
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // 1. API 請求強制使用網絡 (Network Only)
    // 包含公車(iBus)與 YouBike API
    if (url.hostname.includes('ibus.tbkc.gov.tw') || url.hostname.includes('apis.youbike.com.tw')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // 2. 其他資源 (包含地圖圖磚、字型、腳本) 使用 Cache First 策略
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            // 如果快取有，直接回傳
            if (cachedResponse) return cachedResponse;

            // 如果快取沒有，去網絡抓
            return fetch(event.request).then(networkResponse => {
                // 檢查回應是否有效
                if (!networkResponse || networkResponse.status !== 200) {
                    return networkResponse;
                }

                // 只快取同源 (basic) 或明確成功的跨域 (cors) 請求
                // 這是為了避免快取不透明 (opaque) 的錯誤回應
                const responseType = networkResponse.type;
                if (responseType !== 'basic' && responseType !== 'cors') {
                    return networkResponse;
                }

                // 複製回應並存入快取
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });

                return networkResponse;
            }).catch(() => {
                // 當網路請求失敗且快取中也沒有對應資源時會觸發
                // 可選擇性地回傳一個預設的離線頁面或資源
                // console.log('Fetch failed and no cache for:', event.request.url);
            });
        })
    );
});
