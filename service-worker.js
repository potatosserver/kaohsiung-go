// Service Worker Version
// 更新版本號為 v3 以確保新設定生效 (會清除舊快取)
const CACHE_NAME = 'kh-transport-v3';

// 這些資源會被安裝時預先快取
const STATIC_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './icons/icon.ico',
    './icons/icon-192x192.png', // 新增：補上這個圖示，解決找不到檔案的錯誤
    
    // Leaflet 核心與聚合套件 (CDN)
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.css',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.Default.css',
    'https://unpkg.com/leaflet.markercluster/dist/leaflet.markercluster.js',
    
    // UI 樣式與字型 (CDN)
    'https://cdn.tailwindcss.com',
    'https://fonts.googleapis.com/icon?family=Material+Icons+Outlined|Material+Icons+Round',
    'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap'
];

// 安裝階段：預先下載靜態資源
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('[SW] Pre-caching offline assets');
            // 使用 addAll 下載所有檔案
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
                    console.log('[SW] Removing old cache', key);
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
    // 包含: 公車(iBus)、YouBike、捷運輕軌(traffic.tbkc)、以及 Proxy 服務
    if (url.hostname.includes('ibus.tbkc.gov.tw') || 
        url.hostname.includes('apis.youbike.com.tw') ||
        url.hostname.includes('traffic.tbkc.gov.tw') || // 新增：捷運輕軌 API 也不要快取
        url.href.includes('corsproxy.io') ||            // 新增：Proxy 也不要快取
        url.href.includes('workers.dev')) {
        
        // 對於 API，直接回傳網路請求，失敗就失敗 (由網頁端 JS 處理錯誤)
        event.respondWith(fetch(event.request));
        return;
    }

    // 2. 其他資源 (包含地圖圖磚、字型、腳本) 使用 Cache First 策略
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            // A. 如果快取有，直接回傳 (離線成功的關鍵)
            if (cachedResponse) return cachedResponse;

            // B. 如果快取沒有，去網絡抓
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

                // 複製回應並存入快取 (動態快取機制)
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });

                return networkResponse;
            }).catch(() => {
                // C. 網路請求失敗且快取中也沒有對應資源
                // 這裡可以選擇性地回傳一個預設的離線圖示或頁面，目前保持空白即可
                // console.log('Fetch failed and no cache for:', event.request.url);
            });
        })
    );
});
