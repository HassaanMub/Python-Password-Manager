"""
models.py
=========

Data model definitions for the Password Manager application.
This module defines the core entities used throughout the application:
- ``PasswordRecord``: represents a single saved credential entry (either
  custom credentials or a Google-linked account reference).
- ``GoogleAccount``: represents a Google account that can be linked to
  one or more password records.
Both classes implement ``to_dict`` / ``from_dict`` methods to support
clean JSON serialization and deserialization, keeping persistence logic
decoupled from the data shape itself.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict

def _timestamp() -> str:
    """Return the current timestamp as an ISO-8601 formatted string.
    Returns:
        str: Current date and time in ISO-8601 format
        (e.g. ``2024-01-15T10:30:00``).
    """
    return datetime.now().isoformat(timespec="seconds")

def _generate_id() -> str:
    """Generate a short, unique identifier for a record.
    Returns:
        str: An 8-character hexadecimal unique identifier.
    """
    return uuid.uuid4().hex[:8]

@dataclass
class GoogleAccount:
    """Represents a Google account that can be linked to password records.
    Attributes:
        email (str): The Google account email address. Acts as the
            unique key for the account (duplicates are not allowed).
        created_at (str): ISO-8601 timestamp of when the account was added.
    """
    email: str
    created_at: str = field(default_factory=_timestamp)
    def to_dict(self) -> Dict[str, Any]:
        """Convert this GoogleAccount into a JSON-serializable dictionary.
        Returns:
            Dict[str, Any]: Dictionary representation of the account.
        """
        return asdict(self)
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoogleAccount":
        """Build a GoogleAccount instance from a plain dictionary.
        Args:
            data (Dict[str, Any]): Dictionary loaded from JSON storage.
        Returns:
            GoogleAccount: A reconstructed GoogleAccount instance.
        """
        return cls(
            email=data.get("email", ""),
            created_at=data.get("created_at", _timestamp()),
        )

@dataclass
class PasswordRecord:
    """Represents a single password/credential entry.
    A record can either hold "custom" credentials (username, email,
    phone, password) or be "google" linked, in which case it references
    a Google account email instead of storing a separate password.
    Attributes:
        id (str): Unique identifier for the record.
        title (str): Human-readable name of the entry (e.g. "Github").
        category (str): Category label (e.g. "Development", "Social").
        login_type (str): Either ``"custom"`` or ``"google"``.
        username (str): Username for custom credentials (optional).
        email (str): Email for custom credentials.
        phone (str): Phone number for custom credentials (optional).
        password (str): Password for custom credentials.
        google_email (str): Linked Google account email (if applicable).
        website (str): Associated website URL (optional).
        notes (str): Free-form notes (optional).
        favorite (bool): Whether the record is marked as a favorite.
        created_at (str): ISO-8601 creation timestamp.
        updated_at (str): ISO-8601 last-updated timestamp.
    """
    title: str
    category: str
    login_type: str
    username: str = ""
    email: str = ""
    phone: str = ""
    password: str = ""
    google_email: str = ""
    website: str = ""
    notes: str = ""
    favorite: bool = False
    id: str = field(default_factory=_generate_id)
    created_at: str = field(default_factory=_timestamp)
    updated_at: str = field(default_factory=_timestamp)
    def touch(self) -> None:
        """Update the ``updated_at`` timestamp to the current time.
        Should be called any time a record's fields are modified.
        """
        self.updated_at = _timestamp()
    def to_dict(self) -> Dict[str, Any]:
        """Convert this PasswordRecord into a JSON-serializable dictionary.
        Returns:
            Dict[str, Any]: Dictionary representation of the record.
        """
        return asdict(self)
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PasswordRecord":
        """Build a PasswordRecord instance from a plain dictionary.
        Missing keys fall back to sensible defaults so that older or
        partially-written JSON entries do not crash the application.
        Args:
            data (Dict[str, Any]): Dictionary loaded from JSON storage.
        Returns:
            PasswordRecord: A reconstructed PasswordRecord instance.
        """
        return cls(
            id=data.get("id", _generate_id()),
            title=data.get("title", ""),
            category=data.get("category", "Other"),
            login_type=data.get("login_type", "custom"),
            username=data.get("username", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            password=data.get("password", ""),
            google_email=data.get("google_email", ""),
            website=data.get("website", ""),
            notes=data.get("notes", ""),
            favorite=bool(data.get("favorite", False)),
            created_at=data.get("created_at", _timestamp()),
            updated_at=data.get("updated_at", _timestamp()),
        )
    def matches(self, query: str) -> bool:
        """Check whether a search query partially matches this record.
        The match is case-insensitive and checks the title, category,
        email, google_email, and website fields.
        Args:
            query (str): The search term entered by the user.
        Returns:
            bool: True if the query is found in any searchable field.
        """
        query = query.lower().strip()
        if not query:
            return False
        searchable_fields = (
            self.title,
            self.category,
            self.email,
            self.google_email,
            self.website,
        )
        return any(query in (field_value or "").lower() for field_value in searchable_fields)
    def display_identity(self) -> str:
        """Return the most relevant identity string for display purposes.
        For Google-linked records this is the linked Google email; for
        custom records it falls back to email, then username.
        Returns:
            str: A human-readable identity string.
        """
        if self.login_type == "google":
            return self.google_email or "(no google account linked)"
        return self.email or self.username or "(no identity set)"