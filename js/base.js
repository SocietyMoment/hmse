for (let e of $("span.timestamp-format")) {
    let ts = parseInt(e.dataset.timestamp);
    e.innerHTML = (new Date(ts/1000)).toLocaleString(undefined, {day:"numeric", month:"numeric", hour:"numeric", minute:"2-digit"});
    //e.innerHTML = (new Date(ts/1000)).toLocaleString();
}

$("#stonk-search").on('input', (e)=>{
    let text = e.currentTarget.value.toUpperCase();
    if (text.length>=1) {
        matches = all_stonks_list.filter(s => (s.name.toUpperCase().includes(text) || s.ticker.startsWith(text)));
        let dropdown="";
        for (let s of matches) {
            dropdown += `
                <a onclick="document.location.href=this.href;"
                    class="dropdown-item stonk-search-item" href="/stonks/${s.ticker}">
                    <img src="/img/stonk-icons/icon_${s.id}" class="lead" style="height: 1em; width:auto;">
                    <span style="position: relative; top:0.16em;" class="lead">${s.ticker}</span>
                    <span style="float:right; position: relative; top:.3em;" class="text-muted">${s.name}</span>
                </a>
            `;
        }
        $("#stonk-search-results").html(dropdown)
            .prop("hidden", false)
            .dropdown('show');
    } else {
        $("#stonk-search-results")
            .prop("hidden", true)
            .dropdown('hide');
    }
});

$("#stonk-search-form").on('submit', (e)=>{
    e.preventDefault();
    document.location.href = $("#stonk-search-results")[0].firstElementChild.href;
    return false;
});

$(window).keyup((e)=>{
    if (e.which===191 && !e.ctrlKey && !e.shiftKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        $("#stonk-search").click();
        return false;
    }
});

const urlBase64ToUint8Array = (base64String) => {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
};

function get_sw() {
    return navigator.serviceWorker.register('/js/notification_sw.js', {
        scope: '/',
    });
}

// https://felixgerschau.com/web-push-notifications-tutorial/
let set_up_notifications = async () => {
    if (!('serviceWorker' in navigator && 'PushManager' in window)) return;

    let registration = await get_sw();

    let notif_perm = await Notification.requestPermission();
    if (notif_perm!=="granted") return;

    let sub = await registration.pushManager.getSubscription();
    if (sub!==null) return;

    sub = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    });

    await fetch('/subscribe_notifications', {
        method: 'POST',
        body: JSON.stringify(sub),
        headers: {
            'content-type': 'application/json',
        },
    });
};

let remove_notifications = async () => {
    let registration = await get_sw();

    let sub = await registration.pushManager.getSubscription();
    if (sub===null) return;
    await sub.unsubscribe();
};

