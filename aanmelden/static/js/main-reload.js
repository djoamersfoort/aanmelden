const socket = io()
socket.on('update_main_page', () => location.reload())
window.addEventListener('beforeunload', () => socket.disconnect())