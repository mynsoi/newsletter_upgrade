// 설치(PWA)용 최소 서비스 워커 — 캐시하지 않고 그대로 통과시킨다(작업 상태가 늘 최신이어야 해서)
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
