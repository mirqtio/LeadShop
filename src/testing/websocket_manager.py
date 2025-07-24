"""
PRP-013: WebSocket Manager for Real-time Testing Dashboard Updates
Manages WebSocket connections and real-time communication for the testing interface
"""

import asyncio
import json
import logging
import weakref
from datetime import datetime, timezone
from typing import Dict, Set, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    # System status messages
    SYSTEM_STATUS = "system_status"
    PIPELINE_HEALTH = "pipeline_health"
    
    # Test execution messages
    TEST_STARTED = "test_started"
    TEST_UPDATE = "test_update"
    TEST_COMPLETED = "test_completed"
    TEST_FAILED = "test_failed"
    
    # Lead management messages
    LEAD_IMPORTED = "lead_imported"
    LEAD_UPDATED = "lead_updated"
    
    # Metrics updates
    METRICS_UPDATE = "metrics_update"
    PERFORMANCE_UPDATE = "performance_update"
    
    # Client messages
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

@dataclass
class WebSocketMessage:
    """Structured WebSocket message format."""
    type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[int] = None
    test_id: Optional[str] = None

class WebSocketConnection:
    """Individual WebSocket connection wrapper."""
    
    def __init__(self, websocket, user_id: int):
        self.websocket = websocket
        self.user_id = user_id
        self.subscriptions: Set[str] = set()
        self.connected_at = datetime.now(timezone.utc)
        self.last_ping = datetime.now(timezone.utc)
        self.is_active = True
    
    async def send_message(self, message: WebSocketMessage):
        """Send message to this WebSocket connection."""
        try:
            if not self.is_active:
                return False
            
            message_data = {
                'type': message.type,
                'payload': message.payload,
                'timestamp': message.timestamp.isoformat(),
                'user_id': message.user_id,
                'test_id': message.test_id
            }
            
            await self.websocket.send_text(json.dumps(message_data))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to user {self.user_id}: {e}")
            self.is_active = False
            return False
    
    def subscribe_to_test(self, test_id: str):
        """Subscribe this connection to test updates."""
        self.subscriptions.add(f"test:{test_id}")
    
    def unsubscribe_from_test(self, test_id: str):
        """Unsubscribe this connection from test updates."""
        self.subscriptions.discard(f"test:{test_id}")
    
    def update_ping(self):
        """Update last ping timestamp."""
        self.last_ping = datetime.now(timezone.utc)
    
    def is_subscribed_to(self, subscription: str) -> bool:
        """Check if connection is subscribed to a topic."""
        return subscription in self.subscriptions

class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Store connections by user ID
        self.connections: Dict[int, List[WebSocketConnection]] = {}
        
        # Store connections by test ID for efficient test-specific broadcasting
        self.test_subscriptions: Dict[str, Set[WebSocketConnection]] = {}
        
        # Message queue for reliable delivery
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Connection cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._message_processor_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.total_connections = 0
        self.messages_sent = 0
        self.failed_sends = 0
    
    async def start(self):
        """Start the WebSocket manager background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_connections())
        self._message_processor_task = asyncio.create_task(self._process_message_queue())
        logger.info("WebSocket manager started")
    
    async def stop(self):
        """Stop the WebSocket manager and cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._message_processor_task:
            self._message_processor_task.cancel()
        
        # Close all connections
        for user_connections in self.connections.values():
            for conn in user_connections:
                try:
                    await conn.websocket.close()
                except Exception:
                    pass
        
        self.connections.clear()
        self.test_subscriptions.clear()
        logger.info("WebSocket manager stopped")
    
    async def connect(self, websocket, user_id: int) -> WebSocketConnection:
        """Register a new WebSocket connection."""
        connection = WebSocketConnection(websocket, user_id)
        
        if user_id not in self.connections:
            self.connections[user_id] = []
        
        self.connections[user_id].append(connection)
        self.total_connections += 1
        
        logger.info(f"WebSocket connected for user {user_id}, total connections: {self.get_connection_count()}")
        
        # Send welcome message
        welcome_message = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            payload={
                'status': 'connected',
                'user_id': user_id,
                'server_time': datetime.now(timezone.utc).isoformat()
            },
            timestamp=datetime.now(timezone.utc),
            user_id=user_id
        )
        
        await connection.send_message(welcome_message)
        return connection
    
    async def disconnect(self, websocket, user_id: int):
        """Unregister a WebSocket connection."""
        if user_id not in self.connections:
            return
        
        # Find and remove the connection
        user_connections = self.connections[user_id]
        connections_to_remove = []
        
        for conn in user_connections:
            if conn.websocket == websocket:
                connections_to_remove.append(conn)
                
                # Remove from test subscriptions
                for test_id, subscribers in self.test_subscriptions.items():
                    subscribers.discard(conn)
        
        for conn in connections_to_remove:
            user_connections.remove(conn)
        
        # Clean up empty user connection lists
        if not user_connections:
            del self.connections[user_id]
        
        # Clean up empty test subscriptions
        empty_tests = [test_id for test_id, subscribers in self.test_subscriptions.items() if not subscribers]
        for test_id in empty_tests:
            del self.test_subscriptions[test_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}, total connections: {self.get_connection_count()}")
    
    async def broadcast_to_user(self, user_id: int, message: WebSocketMessage):
        """Send message to all connections for a specific user."""
        if user_id not in self.connections:
            return
        
        message.user_id = user_id
        await self.message_queue.put(('user', user_id, message))
    
    async def broadcast_to_test_subscribers(self, test_id: str, message: WebSocketMessage):
        """Send message to all connections subscribed to a test."""
        if test_id not in self.test_subscriptions:
            return
        
        message.test_id = test_id
        await self.message_queue.put(('test', test_id, message))
    
    async def broadcast_to_all_users(self, message: WebSocketMessage):
        """Send message to all connected users."""
        await self.message_queue.put(('all', None, message))
    
    async def subscribe_to_test(self, websocket, test_id: str):
        """Subscribe a WebSocket connection to test updates."""
        # Find the connection
        connection = None
        for user_connections in self.connections.values():
            for conn in user_connections:
                if conn.websocket == websocket:
                    connection = conn
                    break
            if connection:
                break
        
        if not connection:
            logger.warning(f"Cannot subscribe to test {test_id}: connection not found")
            return
        
        # Add to test subscriptions
        if test_id not in self.test_subscriptions:
            self.test_subscriptions[test_id] = set()
        
        self.test_subscriptions[test_id].add(connection)
        connection.subscribe_to_test(test_id)
        
        logger.info(f"User {connection.user_id} subscribed to test {test_id}")
    
    async def unsubscribe_from_test(self, websocket, test_id: str):
        """Unsubscribe a WebSocket connection from test updates."""
        # Find the connection
        connection = None
        for user_connections in self.connections.values():
            for conn in user_connections:
                if conn.websocket == websocket:
                    connection = conn
                    break
            if connection:
                break
        
        if not connection:
            return
        
        # Remove from test subscriptions
        if test_id in self.test_subscriptions:
            self.test_subscriptions[test_id].discard(connection)
            if not self.test_subscriptions[test_id]:
                del self.test_subscriptions[test_id]
        
        connection.unsubscribe_from_test(test_id)
        logger.info(f"User {connection.user_id} unsubscribed from test {test_id}")
    
    async def handle_client_message(self, websocket, message_data: Dict[str, Any]):
        """Handle incoming client messages."""
        try:
            message_type = message_data.get('type')
            payload = message_data.get('payload', {})
            
            if message_type == MessageType.PING:
                # Respond with pong
                pong_message = WebSocketMessage(
                    type=MessageType.PONG,
                    payload={'server_time': datetime.now(timezone.utc).isoformat()},
                    timestamp=datetime.now(timezone.utc)
                )
                await websocket.send_text(json.dumps(asdict(pong_message)))
                
                # Update ping timestamp
                connection = self._find_connection_by_websocket(websocket)
                if connection:
                    connection.update_ping()
            
            elif message_type == MessageType.SUBSCRIBE:
                test_id = payload.get('test_id')
                if test_id:
                    await self.subscribe_to_test(websocket, test_id)
            
            elif message_type == MessageType.UNSUBSCRIBE:
                test_id = payload.get('test_id')
                if test_id:
                    await self.unsubscribe_from_test(websocket, test_id)
            
            else:
                logger.warning(f"Unknown client message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
    
    def _find_connection_by_websocket(self, websocket) -> Optional[WebSocketConnection]:
        """Find connection object by WebSocket instance."""
        for user_connections in self.connections.values():
            for conn in user_connections:
                if conn.websocket == websocket:
                    return conn
        return None
    
    async def _process_message_queue(self):
        """Process queued messages for delivery."""
        while True:
            try:
                delivery_type, target, message = await self.message_queue.get()
                
                if delivery_type == 'user':
                    await self._deliver_to_user(target, message)
                elif delivery_type == 'test':
                    await self._deliver_to_test_subscribers(target, message)
                elif delivery_type == 'all':
                    await self._deliver_to_all_users(message)
                
                self.message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message queue: {e}")
                await asyncio.sleep(1)
    
    async def _deliver_to_user(self, user_id: int, message: WebSocketMessage):
        """Deliver message to specific user's connections."""
        if user_id not in self.connections:
            return
        
        user_connections = self.connections[user_id][:]  # Copy to avoid modification during iteration
        failed_connections = []
        
        for connection in user_connections:
            success = await connection.send_message(message)
            if success:
                self.messages_sent += 1
            else:
                self.failed_sends += 1
                failed_connections.append(connection)
        
        # Remove failed connections
        for failed_conn in failed_connections:
            try:
                self.connections[user_id].remove(failed_conn)
            except ValueError:
                pass  # Already removed
    
    async def _deliver_to_test_subscribers(self, test_id: str, message: WebSocketMessage):
        """Deliver message to test subscribers."""
        if test_id not in self.test_subscriptions:
            return
        
        subscribers = list(self.test_subscriptions[test_id])  # Copy to avoid modification
        failed_connections = []
        
        for connection in subscribers:
            success = await connection.send_message(message)
            if success:
                self.messages_sent += 1
            else:
                self.failed_sends += 1
                failed_connections.append(connection)
        
        # Remove failed connections from subscriptions
        for failed_conn in failed_connections:
            self.test_subscriptions[test_id].discard(failed_conn)
    
    async def _deliver_to_all_users(self, message: WebSocketMessage):
        """Deliver message to all connected users."""
        all_connections = []
        for user_connections in self.connections.values():
            all_connections.extend(user_connections)
        
        failed_connections = []
        
        for connection in all_connections:
            success = await connection.send_message(message)
            if success:
                self.messages_sent += 1
            else:
                self.failed_sends += 1
                failed_connections.append(connection)
        
        # Remove failed connections
        for failed_conn in failed_connections:
            for user_id, user_connections in self.connections.items():
                try:
                    user_connections.remove(failed_conn)
                except ValueError:
                    continue
    
    async def _cleanup_connections(self):
        """Periodic cleanup of stale connections."""
        while True:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                
                now = datetime.now(timezone.utc)
                stale_connections = []
                
                # Find stale connections (no ping in 5 minutes)
                for user_id, user_connections in self.connections.items():
                    for connection in user_connections[:]:  # Copy to avoid modification
                        time_since_ping = (now - connection.last_ping).total_seconds()
                        
                        if time_since_ping > 300 or not connection.is_active:  # 5 minutes
                            stale_connections.append((user_id, connection))
                
                # Remove stale connections
                for user_id, stale_conn in stale_connections:
                    try:
                        await stale_conn.websocket.close()
                    except Exception:
                        pass
                    
                    try:
                        self.connections[user_id].remove(stale_conn)
                        if not self.connections[user_id]:
                            del self.connections[user_id]
                    except (ValueError, KeyError):
                        pass
                    
                    # Remove from test subscriptions
                    for test_id, subscribers in list(self.test_subscriptions.items()):
                        subscribers.discard(stale_conn)
                        if not subscribers:
                            del self.test_subscriptions[test_id]
                
                if stale_connections:
                    logger.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during connection cleanup: {e}")
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.connections.values())
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of connections for a specific user."""
        return len(self.connections.get(user_id, []))
    
    def get_test_subscriber_count(self, test_id: str) -> int:
        """Get number of subscribers for a specific test."""
        return len(self.test_subscriptions.get(test_id, set()))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            'total_connections': self.get_connection_count(),
            'connected_users': len(self.connections),
            'active_test_subscriptions': len(self.test_subscriptions),
            'messages_sent': self.messages_sent,
            'failed_sends': self.failed_sends,
            'message_queue_size': self.message_queue.qsize(),
            'success_rate': (self.messages_sent / (self.messages_sent + self.failed_sends)) * 100 if (self.messages_sent + self.failed_sends) > 0 else 100
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

# Convenience functions for sending common message types

async def send_test_started(test_id: str, test_data: Dict[str, Any]):
    """Send test started notification."""
    message = WebSocketMessage(
        type=MessageType.TEST_STARTED,
        payload=test_data,
        timestamp=datetime.now(timezone.utc),
        test_id=test_id
    )
    await websocket_manager.broadcast_to_test_subscribers(test_id, message)

async def send_test_update(test_id: str, update_data: Dict[str, Any]):
    """Send test progress update."""
    message = WebSocketMessage(
        type=MessageType.TEST_UPDATE,
        payload=update_data,
        timestamp=datetime.now(timezone.utc),
        test_id=test_id
    )
    await websocket_manager.broadcast_to_test_subscribers(test_id, message)

async def send_test_completed(test_id: str, result_data: Dict[str, Any]):
    """Send test completion notification."""
    message = WebSocketMessage(
        type=MessageType.TEST_COMPLETED,
        payload=result_data,
        timestamp=datetime.now(timezone.utc),
        test_id=test_id
    )
    await websocket_manager.broadcast_to_test_subscribers(test_id, message)

async def send_system_status_update(status_data: Dict[str, Any]):
    """Send system status update to all users."""
    message = WebSocketMessage(
        type=MessageType.SYSTEM_STATUS,
        payload=status_data,
        timestamp=datetime.now(timezone.utc)
    )
    await websocket_manager.broadcast_to_all_users(message)

async def send_metrics_update(metrics_data: Dict[str, Any]):
    """Send metrics update to all users."""
    message = WebSocketMessage(
        type=MessageType.METRICS_UPDATE,
        payload=metrics_data,
        timestamp=datetime.now(timezone.utc)
    )
    await websocket_manager.broadcast_to_all_users(message)