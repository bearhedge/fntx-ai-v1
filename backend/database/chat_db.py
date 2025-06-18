"""
Chat history database for storing user conversations
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import uuid

class ChatMessage:
    def __init__(self, id: str, user_id: str, message: str, response: str, timestamp: datetime):
        self.id = id
        self.user_id = user_id
        self.message = message
        self.response = response
        self.timestamp = timestamp
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'response': self.response,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            message=data['message'],
            response=data['response'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

class ChatDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use project root database directory
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "database" / "chat_history.json"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database if it doesn't exist
        if not self.db_path.exists():
            self._save_db({})
    
    def _load_db(self) -> Dict[str, List[Dict]]:
        """Load the database from file"""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_db(self, data: Dict[str, List[Dict]]):
        """Save the database to file"""
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_message(self, user_id: str, message: str, response: str) -> ChatMessage:
        """Add a new chat message"""
        chat_msg = ChatMessage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            message=message,
            response=response,
            timestamp=datetime.utcnow()
        )
        
        db = self._load_db()
        if user_id not in db:
            db[user_id] = []
        
        db[user_id].append(chat_msg.to_dict())
        
        # Keep only last 100 messages per user
        if len(db[user_id]) > 100:
            db[user_id] = db[user_id][-100:]
        
        self._save_db(db)
        return chat_msg
    
    def get_user_history(self, user_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get chat history for a user"""
        db = self._load_db()
        if user_id not in db:
            return []
        
        messages = db[user_id][-limit:]
        return [ChatMessage.from_dict(msg) for msg in messages]
    
    def clear_user_history(self, user_id: str):
        """Clear chat history for a user"""
        db = self._load_db()
        if user_id in db:
            del db[user_id]
            self._save_db(db)

# Singleton instance
_chat_db_instance = None

def get_chat_db() -> ChatDB:
    """Get the singleton ChatDB instance"""
    global _chat_db_instance
    if _chat_db_instance is None:
        _chat_db_instance = ChatDB()
    return _chat_db_instance