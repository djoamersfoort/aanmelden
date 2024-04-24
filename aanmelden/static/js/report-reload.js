const socket = io()
let skipReload = false

socket.on('update_report_page', () => {
    if(skipReload) {
        skipReload = false
        return
    }
    location.reload()
})

document.addEventListener('input', (event) => {
    let url = event.target.dataset.requestUrl
    if(!url) return

    skipReload = true
    url = url.replace('::', event.target.checked)
    fetch(url)
})

window.addEventListener('beforeunload', () => socket.disconnect())
