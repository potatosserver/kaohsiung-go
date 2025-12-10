// Service Worker Version
// 更新版本號為 v5 以確保新設定生效 (會清除舊快取)
const CACHE_NAME = 'kh-transport-v5';

// 可以正常快取的資源
const NORMAL_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    './icons/icon.ico',
    './icons/icon-192x192.png',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.css',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.Default.css',
    'https://unpkg.com/leaflet.markercluster/dist/leaflet.markercluster.js',
    'https://fonts.googleapis.com/icon?family=Material+Icons+Outlined|Material+Icons+Round',
    'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap'
];

// TailwindCSS 需要使用 no-cors 模式特殊處理
const TAILWIND_ASSET = 'https://cdn.tailwindcss.com';

// 安裝階段
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(async (cache) => {
            console.log('[SW] Pre-caching standard assets');
            await cache.addAll(NORMAL_ASSETS);

            console.log('[SW] Caching Tailwind CSS with no-cors');
            try {
                const request = new Request(TAILWIND_ASSET, { mode: 'no-cors' });
                const response = await fetch(request);
                await cache.put(request, response);
            } catch (error) {
                console.error('[SW] Failed to cache Tailwind CSS:', error);
            }
        })
    );
    self.skipWaiting();
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
    self.clients.claim();
});

// 攔截請求
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // *** 關鍵修正 ***
    // 1. 對於 API 請求，完全不要處理 (不呼叫 event.respondWith)，
    //    讓請求回到瀏覽器，以便被 App 的原生程式碼攔截。
    if (url.hostname.includes('ibus.tbkc.gov.tw') ||
        url.hostname.includes('apis.youbike.com.tw') ||
        url.hostname.includes('traffic.tbkc.gov.tw') ||
        url.href.includes('corsproxy.io') ||
        url.href.includes('workers.dev')) {
        // 直接返回，不做任何事
        return;
    }

    // 2. 其他資源使用 Cache First 策略
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            if (cachedResponse) return cachedResponse;

            return fetch(event.request).then(networkResponse => {
                const responseType = networkResponse.type;
                if (responseType !== 'basic' && responseType !== 'cors') {
                    return networkResponse;
                }
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });
                return networkResponse;
            }).catch(() => {
                // 處理網路請求失敗的情況
            });
        })
    );
});
