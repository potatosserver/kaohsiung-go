// Service Worker Version
// 更新版本號以觸發 activate 事件清除舊快取
const CACHE_NAME = 'kh-transport-vector-v1';

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
    
    // [新] MapLibre GL (向量地圖引擎)
    'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css',
    'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js',
    'https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.0.21/leaflet-maplibre-gl.js',

    // [新] 地圖樣式檔 (確保離線能讀取樣式設定)
    'https://potatosserver.github.io/map/shortbread.json',
    
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

                // 檢查是否為可以快取的類型
                // type 'basic': 同源請求
                // type 'cors': 跨域請求 (CDN, 地圖圖磚, 字型檔通常是這個)
                // type 'opaque': 不透明回應 (通常不建議快取，但在某些圖片資源可能需要)
                const responseType = networkResponse.type;
                if (responseType !== 'basic' && responseType !== 'cors') {
                    // 如果不是 basic 或 cors (例如 opaque)，視情況決定是否不快取
                    // 為了安全起見，這裡只快取明確成功的 cors 資源
                    // 但有些地圖資源可能是 opaque，若地圖出不來可考慮放寬
                    // 目前設定：只快取 Basic 和 CORS
                    return networkResponse;
                }

                // 複製回應並存入快取
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });

                return networkResponse;
            }).catch(() => {
                // 離線且快取沒資料時的 fallback (可選)
                // console.log('Fetch failed and no cache for:', event.request.url);
            });
        })
    );
});
