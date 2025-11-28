// Service Worker Version
const CACHE_NAME = 'kh-transport-v1';

// 這些資源會被快取，加快載入速度
const STATIC_ASSETS = [
    './index.html',
    './manifest.json',
    './icons/icon.ico',  // 新增：快取圖示
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.css',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.Default.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet.markercluster/dist/leaflet.markercluster.js',
    'https://cdn.tailwindcss.com',
    'https://fonts.googleapis.com/icon?family=Material+Icons+Outlined|Material+Icons+Round',
    'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap'
];

// 安裝階段：快取靜態資源
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('SW: Pre-caching offline assets');
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// 啟用階段：清除舊快取
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

// 攔截請求
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // 1. 如果是 API 請求 (iBus, YouBike)，強制使用網絡 (Network Only)
    if (url.hostname.includes('ibus.tbkc.gov.tw') || url.hostname.includes('apis.youbike.com.tw')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // 2. 對於其他資源，使用 Cache First 策略
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            if (cachedResponse) return cachedResponse;
            return fetch(event.request).then(networkResponse => {
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    if(networkResponse.type !== 'cors' && networkResponse.type !== 'opaque') {
                        return networkResponse;
                    }
                }
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });
                return networkResponse;
            });
        })
    );
});
