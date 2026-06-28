"""
manager.py
==========
Core business logic and persistence layer for the Password Manager.

This module defines the ``PasswordManager`` class, which is responsible
for:

- Loading and saving data to/from the JSON storage file.
- Creating, reading, updating, and deleting password records.
- Managing the list of linked Google accounts.
- Providing search, sort, and statistics functionality.

By isolating all storage and data-manipulation logic here, ``main.py``
stays focused purely on presenting menus and collecting user input.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Dict, List, Optional

from models import GoogleAccount, PasswordRecord


class StorageError(Exception):
    """Raised when the JSON storage file cannot be read or written."""


class PasswordManager:
    """Manages persistence and operations for password records and
    Google accounts.
    The manager owns a single JSON file on disk and keeps an in-memory
    cache of records and Google accounts, which it loads on startup
    and writes back to disk after every mutation.
    Attributes:
        file_path (str): Path to the JSON storage file.
        records (List[PasswordRecord]): In-memory list of password records.
        google_accounts (List[GoogleAccount]): In-memory list of linked
            Google accounts.
    """

    def __init__(self, file_path: str = "passwords.json", text_file_path: Optional[str] = None) -> None:
        """Initialize the manager and load existing data from disk.

        Args:
            file_path (str): Path to the JSON file used for storage.
                The file is created automatically if it does not exist.
            text_file_path (Optional[str]): Path to a plain-text log file
                that new records are appended to. Defaults to the same
                name as ``file_path`` with a ``.txt`` extension. This file
                is write-only/append-only from the application's point of
                view -- it is never read from or used to load data.
        """
        self.file_path = file_path
        if text_file_path is None:
            base, _ = os.path.splitext(file_path)
            text_file_path = f"{base}.txt"
        self.text_file_path = text_file_path
        self.records: List[PasswordRecord] = []
        self.google_accounts: List[GoogleAccount] = []
        self._load()
    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _default_data(self) -> Dict[str, list]:
        """Return the default empty data structure.
        Returns:
            Dict[str, list]: A dictionary with empty "records" and
            "google_accounts" lists.
        """
        return {"records": [], "google_accounts": []}

    def _load(self) -> None:
        """Load records and Google accounts from the JSON file.

        If the file does not exist, it is created with an empty default
        structure. If the file exists but is empty or contains invalid
        JSON, the corrupted file is backed up (with a ``.bak`` suffix)
        and a fresh empty structure is used instead, so the application
        never crashes on startup due to bad data.

        Raises:
            StorageError: If the file exists but cannot be read due to
                a filesystem-level error (e.g. permission denied).
        """
        if not os.path.exists(self.file_path):
            self._write_data(self._default_data())
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_content = f.read().strip()
        except OSError as exc:
            raise StorageError(f"Could not read storage file: {exc}") from exc
        if not raw_content:
            # Empty file -- treat as fresh storage.
            self._write_data(self._default_data())
            return

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            # Corrupted JSON -- back up the bad file and start fresh
            # rather than crashing or silently destroying user data.
            backup_path = f"{self.file_path}.bak"
            try:
                shutil.copy(self.file_path, backup_path)
                print(
                    f"⚠ Warning: '{self.file_path}' contained invalid JSON. "
                    f"A backup was saved to '{backup_path}' and a fresh "
                    f"storage file has been created."
                )
            except OSError:
                print(
                    f"⚠ Warning: '{self.file_path}' contained invalid JSON "
                    f"and could not be backed up. Starting with empty data."
                )
            data = self._default_data()
            self._write_data(data)

        records_data = data.get("records", []) if isinstance(data, dict) else []
        accounts_data = data.get("google_accounts", []) if isinstance(data, dict) else []

        self.records = [PasswordRecord.from_dict(r) for r in records_data if isinstance(r, dict)]
        self.google_accounts = [
            GoogleAccount.from_dict(a) for a in accounts_data if isinstance(a, dict)
        ]

    def _write_data(self, data: Dict[str, list]) -> None:
        """Write a raw data dictionary to the JSON file.
        Args:
            data (Dict[str, list]): The data structure to serialize.
        Raises:
            StorageError: If the file cannot be written.
        """
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError as exc:
            raise StorageError(f"Could not write storage file: {exc}") from exc

    def save(self) -> None:
        """Persist the current in-memory state to the JSON file.
        Raises:
            StorageError: If the underlying write operation fails.
        """
        data = {
            "records": [r.to_dict() for r in self.records],
            "google_accounts": [a.to_dict() for a in self.google_accounts],
        }
        self._write_data(data)

    def _append_record_to_text_file(self, record: PasswordRecord) -> None:
        """Append a single record's summary to the plain-text log file.

        This is append-only: the text file is never read from or used
        to load application state. The JSON file remains the sole
        source of truth; this file exists purely as a human-readable
        running log. Only a subset of fields is written:
        title, username (if present), phone (if present), email,
        and password -- or, for Google-linked records, the linked
        Google email together with a "Linked to Google" marker.

        Args:
            record (PasswordRecord): The record to log.

        Raises:
            StorageError: If the text file cannot be written to.
        """
        lines = [f"Title: {record.title}"]
        if record.login_type == "google":
            lines.append(f"Google Email: {record.google_email}")
            lines.append("Linked to Google")
        else:
            if record.username:
                lines.append(f"Username: {record.username}")
            if record.phone:
                lines.append(f"Phone: {record.phone}")
            lines.append(f"Email: {record.email}")
            lines.append(f"Password: {record.password}")
        entry = "\n".join(lines) + "\n" + ("-" * 30) + "\n"
        try:
            with open(self.text_file_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except OSError as exc:
            raise StorageError(f"Could not write to text log file: {exc}") from exc

    # ------------------------------------------------------------------
    # Record CRUD operations
    # ------------------------------------------------------------------
    def add_record(self, record: PasswordRecord) -> PasswordRecord:
        """Add a new password record and persist the change.
        Args:
            record (PasswordRecord): The record to add.

        Returns:
            PasswordRecord: The same record, after being stored.
        """
        self.records.append(record)
        self.save()
        self._append_record_to_text_file(record)
        return record
    def get_record_by_index(self, index: int) -> Optional[PasswordRecord]:
        """Retrieve a record by its 1-based display index.
        Args:
            index (int): The 1-based index as shown in a listing.
        Returns:
            Optional[PasswordRecord]: The matching record, or None if
            the index is out of range.
        """
        if 1 <= index <= len(self.records):
            return self.records[index - 1]
        return None
    def delete_record(self, record: PasswordRecord) -> None:
        """Delete a record and persist the change.
        Args:
            record (PasswordRecord): The record to remove.
        """
        if record in self.records:
            self.records.remove(record)
            self.save()
    def update_record(self, record: PasswordRecord) -> None:
        """Persist changes made to an existing record.
        Since records are mutated in place, this simply touches the
        ``updated_at`` timestamp and writes the current state to disk.
        Args:
            record (PasswordRecord): The record that was edited.
        """
        record.touch()
        self.save()
    def toggle_favorite(self, record: PasswordRecord) -> None:
        """Flip the favorite status of a record and persist the change.
        Args:
            record (PasswordRecord): The record to toggle.
        """
        record.favorite = not record.favorite
        record.touch()
        self.save()
    def search_records(self, query: str) -> List[PasswordRecord]:
        """Search records by title, category, email, or website.
        Matching is partial and case-insensitive.
        Args:
            query (str): The search term.
        Returns:
            List[PasswordRecord]: Records matching the query, in their
            original order.
        """
        return [r for r in self.records if r.matches(query)]
    def sort_records(self, key: str) -> List[PasswordRecord]:
        """Return a sorted copy of the records list.
        Args:
            key (str): One of "title", "category", "newest", "oldest",
                or "favorites".
        Returns:
            List[PasswordRecord]: A new sorted list (the original list
            order on disk is left untouched).
        """
        if key == "title":
            return sorted(self.records, key=lambda r: r.title.lower())
        if key == "category":
            return sorted(self.records, key=lambda r: r.category.lower())
        if key == "newest":
            return sorted(self.records, key=lambda r: r.created_at, reverse=True)
        if key == "oldest":
            return sorted(self.records, key=lambda r: r.created_at)
        if key == "favorites":
            return sorted(self.records, key=lambda r: not r.favorite)
        return list(self.records)
    # ------------------------------------------------------------------
    # Google account operations
    # ------------------------------------------------------------------
    def add_google_account(self, email: str) -> Optional[GoogleAccount]:
        """Add a new Google account if its email is not already present.
        Args:
            email (str): The Google account email to add.
        Returns:
            Optional[GoogleAccount]: The newly created account, or None
            if an account with that email already exists.
        """
        if self.find_google_account(email) is not None:
            return None
        account = GoogleAccount(email=email)
        self.google_accounts.append(account)
        self.save()
        return account
    def find_google_account(self, email: str) -> Optional[GoogleAccount]:
        """Find a Google account by exact (case-insensitive) email match.
        Args:
            email (str): The email address to look up.
        Returns:
            Optional[GoogleAccount]: The matching account, or None.
        """
        email_lower = email.strip().lower()
        for account in self.google_accounts:
            if account.email.strip().lower() == email_lower:
                return account
        return None
    def get_google_account_by_index(self, index: int) -> Optional[GoogleAccount]:
        """Retrieve a Google account by its 1-based display index.
        Args:
            index (int): The 1-based index as shown in a listing.
        Returns:
            Optional[GoogleAccount]: The matching account, or None if
            the index is out of range.
        """
        if 1 <= index <= len(self.google_accounts):
            return self.google_accounts[index - 1]
        return None
    # ------------------------------------------------------------------
    # Statistics & backup
    # ------------------------------------------------------------------
    def get_statistics(self) -> Dict[str, int]:
        """Compute summary statistics about the stored data.
        Returns:
            Dict[str, int]: A dictionary with total records, favorites,
            Google-linked accounts, and custom accounts counts.
        """
        total = len(self.records)
        favorites = sum(1 for r in self.records if r.favorite)
        google_linked = sum(1 for r in self.records if r.login_type == "google")
        custom = sum(1 for r in self.records if r.login_type == "custom")
        return {
            "total_passwords": total,
            "favorite_passwords": favorites,
            "google_linked_accounts": google_linked,
            "custom_accounts": custom,
            "saved_google_accounts": len(self.google_accounts),
        }
    def export_backup(self, backup_path: str) -> None:
        """Export the current data to a separate backup JSON file.
        Args:
            backup_path (str): Destination path for the backup file.
        Raises:
            StorageError: If the backup file cannot be written.
        """
        data = {
            "records": [r.to_dict() for r in self.records],
            "google_accounts": [a.to_dict() for a in self.google_accounts],
        }
        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError as exc:
            raise StorageError(f"Could not write backup file: {exc}") from exc
    def import_backup(self, backup_path: str, merge: bool = False) -> int:
        """Import data from a backup JSON file.
        Args:
            backup_path (str): Path to the backup JSON file to import.
            merge (bool): If True, imported records/accounts are added
                to the existing data. If False, existing data is
                replaced entirely.
        Returns:
            int: The number of records imported.
        Raises:
            StorageError: If the file does not exist or contains
                invalid JSON.
        """
        if not os.path.exists(backup_path):
            raise StorageError(f"Backup file not found: {backup_path}")
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Could not read backup file: {exc}") from exc
        records_data = data.get("records", []) if isinstance(data, dict) else []
        accounts_data = data.get("google_accounts", []) if isinstance(data, dict) else []
        imported_records = [PasswordRecord.from_dict(r) for r in records_data if isinstance(r, dict)]
        imported_accounts = [
            GoogleAccount.from_dict(a) for a in accounts_data if isinstance(a, dict)
        ]
        if merge:
            self.records.extend(imported_records)
            existing_emails = {a.email.lower() for a in self.google_accounts}
            for account in imported_accounts:
                if account.email.lower() not in existing_emails:
                    self.google_accounts.append(account)
                    existing_emails.add(account.email.lower())
        else:
            self.records = imported_records
            self.google_accounts = imported_accounts
        self.save()
        return len(imported_records)