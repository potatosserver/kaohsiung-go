// Service Worker Version
// 更新版本號為 v4 以確保新設定生效 (會清除舊快取)
const CACHE_NAME = 'kh-transport-v4';

// 可以正常快取的資源
const NORMAL_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './icons/icon.ico',
    './icons/icon-192x192.png',
    
    // Leaflet 核心與聚合套件 (CDN)
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.css',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.Default.css',
    'https://unpkg.com/leaflet.markercluster/dist/leaflet.markercluster.js',
    
    // 字型 (CDN)
    'https://fonts.googleapis.com/icon?family=Material+Icons+Outlined|Material+Icons+Round',
    'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap'
];

// TailwindCSS 需要使用 no-cors 模式特殊處理
const TAILWIND_ASSET = 'https://cdn.tailwindcss.com';

// 安裝階段：預先下載靜態資源
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(async (cache) => { // 使用 async 函數
            console.log('[SW] Pre-caching standard assets');
            // 1. 使用 addAll 快取可以正常請求的資源
            await cache.addAll(NORMAL_ASSETS);

            console.log('[SW] Caching Tailwind CSS with no-cors');
            // 2. 對於 Tailwind CSS，使用 no-cors 模式單獨請求並快取
            try {
                // 建立一個 no-cors 請求
                const request = new Request(TAILWIND_ASSET, { mode: 'no-cors' });
                // 發送請求
                const response = await fetch(request);
                // 將請求和回應存入快取
                await cache.put(request, response);
            } catch (error) {
                console.error('[SW] Failed to cache Tailwind CSS:', error);
                // 即使 Tailwind 快取失敗，也不要讓整個 Service Worker 安裝失敗
            }
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
        url.hostname.includes('traffic.tbkc.gov.tw') ||
        url.href.includes('corsproxy.io') ||
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
            });
        })
    );
});
