# File: db/schemas.py
from typing import Optional, List
from pydantic import BaseModel, Field

class ChatMessageRecord(BaseModel):
    """Schema for persistent chat history records retrieved from the database."""
    role: str = Field(..., description="The role of the sender: 'human' or 'ai'")
    content: str = Field(..., description="The content of the message")
    timestamp: str = Field(..., description="The ISO formatted timestamp of the message")

class MessageRecord(BaseModel):
    """Schema for raw message evidence extracted from UFDR data."""
    id: int
    sender: str
    receiver: str
    timestamp: str
    message: str

class CallRecord(BaseModel):
    """Schema for call logs found in the evidence repository."""
    id: int
    caller: str
    receiver: str
    timestamp: str
    call_duration_seconds: int
    call_type: str

class ContactRecord(BaseModel):
    """Schema for contact address book entries."""
    id: int
    name: str
    phone: str

class TimelineRecord(BaseModel):
    """Schema for system or user timeline event evidence."""
    id: int
    timestamp: str
    event_type: str
    user_name: str
    details: str

class MediaRecord(BaseModel):
    """Schema for forensic media metadata sharing records."""
    id: int
    sender: str
    receiver: str
    timestamp: str
    file_path: str
    file_name: Optional[str]
    file_type: str

class GraphNode(BaseModel):
    """Schema representing a person node in the forensic network graph."""
    id: str
    label: str
    community: str
    pagerank: float
    betweenness: float
    degree: float

class GraphEdge(BaseModel):
    """Schema representing an interaction edge between two people in the network."""
    source: str
    target: str
    type: str
    weight: int
    duration: int

class NetworkGraphRecord(BaseModel):
    """Root schema for the complete cached network topology JSON."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]