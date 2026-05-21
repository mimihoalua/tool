/* ============================================================
   LifeOS.Cloud Service Worker
   File path: /tool/sw_lifeos.js
   Scope    : /tool/
   Purpose  : PWA cache an toàn cho LifeOS trên GitHub Pages
   ============================================================ */

const LIFEOS_SW_VERSION = 'lifeos-sw-v1-20260521';
const CACHE_NAME = 'lifeos-tool-cache-v1-20260521';

/*
  Chỉ cache các file cùng domain /tool/ cần thiết.
  Không cache API thời tiết ở đây vì Weather module đã có localStorage cache riêng.
  Không cache Firebase / Google / Open-Meteo cưỡng ép để tránh lỗi CORS/opaque response.
*/
const CORE_ASSETS = [
  '/tool/lifeos.html',
  '/tool/manifest_lifeos.json',
  '/tool/jsOTP.min.js',
  '/tool/firebase-app-compat.js',
  '/tool/firebase-firestore-compat.js',
  '/tool/firebase-auth-compat.js',
  '/tool/silence_30min.mp3'
];

/* ------------------------------------------------------------
   Install: cài cache lõi, nhưng không làm fail toàn bộ nếu 1 file thiếu
   ------------------------------------------------------------ */
self.addEventListener('install', (event) => {
  console.log('[LifeOS SW] install', LIFEOS_SW_VERSION);

  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      await Promise.all(
        CORE_ASSETS.map(async (url) => {
          try {
            const response = await fetch(url, { cache: 'reload' });
            if (response && response.ok) {
              await cache.put(url, response.clone());
              console.log('[LifeOS SW] cached:', url);
            } else {
              console.warn('[LifeOS SW] skip cache, bad response:', url, response && response.status);
            }
          } catch (err) {
            console.warn('[LifeOS SW] cache failed:', url, err);
          }
        })
      );
    }).then(() => self.skipWaiting())
  );
});

/* ------------------------------------------------------------
   Activate: xóa cache cũ, chiếm quyền ngay
   ------------------------------------------------------------ */
self.addEventListener('activate', (event) => {
  console.log('[LifeOS SW] activate', LIFEOS_SW_VERSION);

  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[LifeOS SW] delete old cache:', key);
            return caches.delete(key);
          }
          return Promise.resolve();
        })
      );
    }).then(() => self.clients.claim())
  );
});

/* ------------------------------------------------------------
   Helper: chỉ xử lý GET request
   ------------------------------------------------------------ */
function isGetRequest(request) {
  return request && request.method === 'GET';
}

/* ------------------------------------------------------------
   Helper: request cùng origin và nằm trong /tool/
   ------------------------------------------------------------ */
function isToolSameOrigin(requestUrl) {
  try {
    const url = new URL(requestUrl);
    return url.origin === self.location.origin && url.pathname.startsWith('/tool/');
  } catch (e) {
    return false;
  }
}

/* ------------------------------------------------------------
   Strategy 1: HTML/navigation network-first, fallback cache
   ------------------------------------------------------------ */
async function handleNavigation(request) {
  try {
    const fresh = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put('/tool/lifeos.html', fresh.clone()).catch(() => {});
    return fresh;
  } catch (err) {
    const cached = await caches.match('/tool/lifeos.html');
    if (cached) return cached;

    return new Response(
      '<!doctype html><html><head><meta charset="utf-8"><title>LifeOS Offline</title></head><body><h1>LifeOS đang offline</h1><p>Không tìm thấy bản cache. Hãy mở lại khi có mạng.</p></body></html>',
      {
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
        status: 200
      }
    );
  }
}

/* ------------------------------------------------------------
   Strategy 2: same-origin /tool assets stale-while-revalidate
   ------------------------------------------------------------ */
async function handleToolAsset(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const networkFetch = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        cache.put(request, response.clone()).catch(() => {});
      }
      return response;
    })
    .catch(() => null);

  return cached || networkFetch || fetch(request);
}

/* ------------------------------------------------------------
   Strategy 3: external requests network-only
   Weather/Firebase/CDN tự xử lý riêng, không ép cache ở SW.
   ------------------------------------------------------------ */
function handleExternal(request) {
  return fetch(request);
}

/* ------------------------------------------------------------
   Fetch router
   ------------------------------------------------------------ */
self.addEventListener('fetch', (event) => {
  const request = event.request;

  if (!isGetRequest(request)) return;

  const url = new URL(request.url);

  /*
    Navigation request: khi mở /tool/lifeos.html hoặc reload app
  */
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(request));
    return;
  }

  /*
    Chỉ cache tài nguyên cùng origin trong /tool/
  */
  if (isToolSameOrigin(request.url)) {
    event.respondWith(handleToolAsset(request));
    return;
  }

  /*
    CDN, Firebase, Open-Meteo, Google Fonts... để network-only
  */
  event.respondWith(handleExternal(request));
});

/* ------------------------------------------------------------
   Message commands: dùng để ép update/clear cache nếu sau này cần
   ------------------------------------------------------------ */
self.addEventListener('message', (event) => {
  const data = event.data || {};

  if (data.type === 'LIFEOS_SKIP_WAITING') {
    self.skipWaiting();
  }

  if (data.type === 'LIFEOS_CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
    );
  }
});
