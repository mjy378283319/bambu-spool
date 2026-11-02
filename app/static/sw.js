/* 拓竹耗材管家 · PWA Service Worker
 *
 * 只做「网络直通」，不缓存任何资源：
 *  - 应用是单页且更新频繁，缓存旧脚本的代价远大于离线可用的收益
 *    （历史上踩过「镜像已更新、页面还是旧 JS」的坑）。
 *  - 保留 fetch 监听只是为满足浏览器「可安装」判定，不改变任何请求行为。
 */
self.addEventListener('install', function () {
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') return;
  var url;
  try {
    url = new URL(event.request.url);
  } catch (e) {
    return;
  }
  // 只接管同源请求，跨源（若有）一律交给浏览器默认处理。
  if (url.origin !== self.location.origin) return;
  event.respondWith(fetch(event.request));
});
