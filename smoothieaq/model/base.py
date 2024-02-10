from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, Annotated


@dataclass
class Identified:
    id: Optional[str] = None


@dataclass
class Named(Identified):
    name: Optional[str] = None


@dataclass
class Described(Identified):
    description: Optional[str] = None


@dataclass
class Document(Identified):
    stamp: Optional[datetime] = None
