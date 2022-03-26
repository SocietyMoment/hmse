self.addEventListener('push', (e) => {
    const data = e.data.json();
    let msg = data.text;
    if (data.color==="success")
        msg = "\u2705 "+msg;
    else if (data.color==="danger")
        msg = "\u274C "+msg;
    self.registration.showNotification(data.title, {
        body: msg,
        icon: "/img/favicon.png",
        badge: "/img/favicon.png",
        timestamp: data.timestamp,
        // https://gearside.com/custom-vibration-patterns-mobile-devices/#
        // Star Wars, tho android doesn't seem to support this
        vibrate: [500,110,500,110,450,110,200,110,170,40,450,110,200,110,170,40,500],
    });
});

self.addEventListener('notificationclick', function(event) {
    // Android doesn’t close the notification when you click on it
    // See: http://crbug.com/463146
    event.notification.close();

    // This looks to see if the current is already open and
    // focuses if it is
    event.waitUntil(clients.matchAll({
        type: 'window'
    }).then(function(clientList) {
        for (let client of clientList)
            if (client.url.endsWith('/notifications') && 'focus' in client) {
                client.navigate('/notifications');
                return client.focus();
            }

        if (clients.openWindow)
            return clients.openWindow('/notifications');
    }));
});

self.addEventListener("install", ()=>{
    self.skipWaiting();
});
