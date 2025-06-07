// 服务工作者缓存配置
const CACHE_NAME = 'v2';
const CACHE_FILES = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/user_data.js',
  '/static/images/logo.png',
  '/favicon.ico'
];

// 安装阶段 - 缓存静态资源
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(CACHE_FILES).catch(err => {
          console.log('Failed to cache:', err);
        });
      })
      .then(() => self.skipWaiting())
  );
});

// 激活阶段 - 清理旧缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// 拦截请求 - 缓存优先策略
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});