import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'progress_{self.user_id}'
        
        # Join WebSocket group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"WebSocket connection accepted for user_id: {self.user_id}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'progress': 0,
            'message': 'Conexión establecida. Esperando inicio de subida.',
            'status': 'info'
        }))

    async def disconnect(self, close_code):
        # Leave WebSocket group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"WebSocket disconnected for user_id: {self.user_id}, code: {close_code}")

    async def receive(self, text_data):
        try:
            # Receive data from WebSocket
            data = json.loads(text_data)
            progress = data.get('progress', 0)
            message = data.get('message', '')
            status = data.get('status', 'info')
            
            # Send message to WebSocket
            await self.send(text_data=json.dumps({
                'progress': progress,
                'message': message,
                'status': status
            }))
        except json.JSONDecodeError:
            # Handle invalid JSON
            await self.send(text_data=json.dumps({
                'progress': 0,
                'message': 'Error: Formato JSON inválido',
                'status': 'error'
            }))
    
    async def progress_message(self, event):
        """
        Handler for messages of type "progress_message"
        """
        message = event.get("message", "")
        progress = event.get("progress", 0)
        status = event.get("status", "info")
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "progress": progress,
            "message": message,
            "status": status
        }))
        print(f"Progress message sent to client: {message}, progress: {progress}, status: {status}")