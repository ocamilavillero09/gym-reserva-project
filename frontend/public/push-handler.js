// Handler de notificaciones push, importado por el service worker (RF14).
self.addEventListener('push', (event) => {
  let data = { title: 'Gimnasio UdeM', body: 'Tienes un recordatorio.' };
  try { data = event.data.json(); } catch (e) { /* payload no-JSON */ }
  event.waitUntil(
    self.registration.showNotification(data.title || 'Gimnasio UdeM', {
      body: data.body || '',
      icon: '/logo-udem.png',
      badge: '/logo-udem.png',
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
