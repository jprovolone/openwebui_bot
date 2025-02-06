# models/data.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class User:
    id: str
    name: str
    profile_image_url: str
    role: str

@dataclass
class AccessControl:
    group_ids: List[str]
    user_ids: List[str]

@dataclass
class ChannelAccessControl:
    read: AccessControl
    write: AccessControl

@dataclass
class Channel:
    id: str
    name: str
    user_id: Optional[str]
    created_at: int
    updated_at: int
    access_control: ChannelAccessControl
    data: Optional[Any] = None
    description: Optional[str] = None
    meta: Optional[Any] = None

@dataclass
class MessageData:
    channel_id: str
    content: str
    created_at: int
    updated_at: int
    user_id: str
    user: User
    id: str
    latest_reply_at: Optional[Any] = None
    reactions: Optional[Any] = None
    reply_count: Optional[int] = 0
    parent_id: Optional[str] = None
    data: Optional[Any] = None
    meta: Optional[Any] = None
    latest_reply_at: Optional[Any] = None
    parent_id: Optional[str] = None
    reactions: Optional[Dict[str, int]] = None
    reply_count: Optional[int] = None

@dataclass
class TypingData:
    typing: bool

@dataclass
class Data:
    type: str
    data: Any

@dataclass
class Event:
    channel_id: str
    data: Data
    user: User
    channel: Optional[Channel] = None
    message_id: Optional[str] = None