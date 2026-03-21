// Nombre del caché 
const CACHE_NAME = 'gym-app-v1';

// Archivos que funcionaran offline
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  '/static/js/bundle.js',
];

// Evento de Instalación: Aquí es donde se guardan los archivos en el caché
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Caché abierto correctamente');
        return cache.addAll(urlsToCache);
      })
  );
});

// Evento de Activación: Limpia cachés viejos si actualizas la versión
self.addEventListener('activate', (event) => {
  console.log('Service Worker activado');
});

// Evento Fetch: Intercepta las peticiones de internet. 
// Si no hay internet, busca el archivo en el caché del celular.
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        return response || fetch(event.request);
      })
  );
});