import socketio

sio = socketio.AsyncServer(async_mode='asgi', logger=True, engineio_logger=True)
