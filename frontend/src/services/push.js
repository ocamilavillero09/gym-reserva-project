import { pushApi } from './api';

// RF14 — Suscribe el navegador a notificaciones push (Web Push API + VAPID).
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export async function enablePush(email) {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    throw new Error('Tu navegador no soporta notificaciones push.');
  }
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') throw new Error('Permiso de notificaciones denegado.');

  const reg = await navigator.serviceWorker.ready;
  const { publicKey } = await pushApi.publicKey();
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
  await pushApi.subscribe(email, sub.toJSON());
  return true;
}
