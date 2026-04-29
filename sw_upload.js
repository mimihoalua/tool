const CACHE_NAME = 'uploader-v30';
self.addEventListener('install', (e) => { 
    self.skipWaiting(); 
});
self.addEventListener('activate', (e) => { 
    e.waitUntil(clients.claim()); 
});
self.addEventListener('fetch', (e) => { 
    // Yêu cầu bắt buộc phải có sự kiện fetch để Chrome công nhận là PWA
});