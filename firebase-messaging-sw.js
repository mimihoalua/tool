// Import bộ SDK thu gọn của Firebase dành cho Service Worker
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js');

// Cấu hình định tuyến giống hệt file HTML
firebase.initializeApp({
    apiKey: "AIzaSyB0yab1ujJturjri9E8HXaknqY4zUwrd3Q",
    authDomain: "tool-mimishop.firebaseapp.com",
    projectId: "tool-mimishop",
    storageBucket: "tool-mimishop.firebasestorage.app",
    messagingSenderId: "536814109954",
    appId: "1:536814109954:web:b1be76d22957de4b75ee1b"
});

const messaging = firebase.messaging();

// Hàm hứng tin nhắn khi App ĐÃ TẮT hoặc ẨN DƯỚI NỀN
messaging.onBackgroundMessage((payload) => {
  console.log('[Firebase SW] Nhận thông báo ngầm: ', payload);
  const notificationTitle = (payload.notification && payload.notification.title) || 'Góc Gia Đình';
  const notificationOptions = {
    body: (payload.notification && payload.notification.body) || 'Bạn có tin nhắn mới',
    icon: 'https://mimihoalua.github.io/tool/icon-192x192.png',
    badge: 'https://mimihoalua.github.io/tool/icon-192x192.png',
    vibrate: [200, 100, 200]
  };
  self.registration.showNotification(notificationTitle, notificationOptions);
});
