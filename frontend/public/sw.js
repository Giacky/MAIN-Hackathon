/* Web Push service worker — shows a notification when the tab is closed. */
self.addEventListener('push', (event) => {
  let title = 'Lost & Found'
  let body = 'You have an update'
  let url = '/'
  try {
    if (event.data) {
      const data = event.data.json()
      if (data.title) title = String(data.title)
      if (data.body) body = String(data.body)
      if (data.url) url = String(data.url)
    }
  } catch {
    /* keep defaults */
  }
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      data: { url },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url)
      return undefined
    }),
  )
})
