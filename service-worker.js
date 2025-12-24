// Service Worker Version: v4 (Update this to force refresh)
const CACHE_NAME = 'kh-transport-v4';

// 核心檔案：這些必須存在，否則 App 無法運作
const CORE_ASSETS = [
    './',
    './index.html',
    './manifest.json',
    // 確保這些檔案真實存在於你的伺服器上，否則 SW 會掛掉
    './icons/icon.ico',
    './icons/icon-192x192.png'
];

// 次要檔案：如果是外部 CDN，建議動態快取，不要放在 install 階段，以免 CDN 掛掉導致整個 App 死掉
// 這裡保留你的 CDN 列表，但建議移到 runtime caching (下方 fetch 邏輯中自動處理)
const OPTIONAL_ASSETS = [
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.css',
    'https://unpkg.com/leaflet.markercluster/dist/MarkerCluster.Default.css',
    'https://unpkg.com/leaflet.markercluster/dist/leaflet.markercluster.js',
    'https://cdn.tailwindcss.com',
    'https://fonts.googleapis.com/icon?family=Material+Icons+Outlined|Material+Icons+Round',
    'https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap'
];

// 安裝階段
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(async cache => {
            console.log('[SW] Installing...');
            
            // 1. 強制快取核心檔案 (如果這步失敗，SW 安裝就會中止，這是正確的)
            await cache.addAll(CORE_ASSETS);
            
            // 2. 嘗試快取外部資源 (CDN)，但如果失敗不影響 SW 安裝
            // 這是避免 CDN 暫時連不上導致你的 App 變成壞掉的狀態
            await Promise.all(
                OPTIONAL_ASSETS.map(url => {
                    return cache.add(url).catch(err => {
                        console.warn('[SW] Failed to pre-cache external asset:', url, err);
                    });
                })
            );
        })
    );
    self.skipWaiting();
});

// 啟用階段：清除舊快取
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => {
                    return caches.delete(key);
                })
            );
        })
    );
    self.clients.claim();
});

// 請求攔截
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // 1. API 請求：永遠走網路 (Network Only)
    if (url.hostname.includes('ibus.tbkc.gov.tw') || 
        url.hostname.includes('apis.youbike.com.tw') ||
        url.hostname.includes('traffic.tbkc.gov.tw') ||
        url.href.includes('corsproxy.io') ||
        url.href.includes('workers.dev')) {
        return; // 直接 return 會走瀏覽器預設網路行為
    }

    // 2. 頁面導航請求 (HTML Navigation) - 這是解決 ERR_FAILED 的關鍵
    // 如果是請求網頁本身 (mode: navigate)，優先走網路，失敗則回傳 index.html
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    // 網路失敗時，回傳快取的 index.html (App Shell)
                    return caches.match('./index.html');
                })
        );
        return;
    }

    // 3. 靜態資源：Stale-While-Revalidate (優先用快取，背景更新) 或 Cache First
    event.respondWith(
        caches.match(event.request).then(cachedResponse => {
            if (cachedResponse) {
                return cachedResponse;
            }
            
            return fetch(event.request).then(networkResponse => {
                // 檢查回應是否有效
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic' && networkResponse.type !== 'cors') {
                    return networkResponse;
                }

                // 動態寫入快取
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });

                return networkResponse;
            }).catch(err => {
                // 圖片等資源載入失敗，可以回傳一個 placeholder，這裡先留空
                // console.log('Fetch failed:', event.request.url);
            });
        })
    );
});
