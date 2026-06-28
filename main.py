"""
main.py
=======
Entry point and console UI for the Password Manager application.
This module is intentionally focused on presentation: it builds the
menus, collects user input, and delegates all data manipulation to the
``PasswordManager`` class (see ``manager.py``) and helper functions in
``utils.py``. Keeping presentation separate from business logic makes
the codebase easier to test, extend, and maintain.

Run this file directly to start the application: python main.py
"""
from __future__ import annotations
import sys
from typing import List, Optional
from manager import PasswordManager, StorageError
from models import PasswordRecord
import utils

STORAGE_FILE = "passwords.json"
CATEGORIES = [
    "Social",
    "Gaming",
    "Development",
    "Streaming",
    "Banking",
    "Shopping",
    "Education",
    "Other",
]

class PasswordManagerApp:
    """Console application that drives the Password Manager menu system.
    Attributes:
        manager (PasswordManager): The underlying data manager instance.
    """
    def __init__(self, manager: PasswordManager) -> None:
        """Initialize the application with a given manager instance.
        Args:
            manager (PasswordManager): The data manager to operate on.
        """
        self.manager = manager
    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the main application loop until the user exits.
        Handles top-level KeyboardInterrupt gracefully so that Ctrl+C
        exits cleanly instead of printing a traceback.
        """
        print("\nWelcome to Your Password Manager!")
        while True:
            try:
                self._show_main_menu()
                choice = input("\nSelect an option (1-15): ").strip()
                self._dispatch(choice)
            except KeyboardInterrupt:
                print("\n\nInterrupted. Exiting safely. Goodbye!")
                sys.exit(0)
            except StorageError as exc:
                print(f"\n✗ Storage error: {exc}")
            except Exception as exc:  # noqa: BLE001 - top level safety net
                print(f"\n✗ An unexpected error occurred: {exc}")
    def _show_main_menu(self) -> None:
        """Print the main menu options to the console."""
        utils.print_header(" PASSWORD MANAGER ")
        print("1. Save New Record")
        print("2. Show All Records")
        print("3. Search Records")
        print("4. Edit Record")
        print("5. Delete Record")
        print("6. Add Google Account")
        print("7. Show Google Accounts")
        print("8. Password Generator")
        print("9. Sort Records")
        print("10. Toggle Favorite")
        print("11. Exit")
        print("12. Statistics")
        print("13. Export Backup")
        print("14. Import Backup")
        print("15. Password Strength Checker")
        utils.print_divider()
    def _dispatch(self, choice: str) -> None:
        """Route a menu choice to the corresponding handler method.
        Args:
            choice (str): The raw string entered by the user.
        """
        actions = {
            "1": self.save_new_record,
            "2": self.show_all_records,
            "3": self.search_records,
            "4": self.edit_record,
            "5": self.delete_record,
            "6": self.add_google_account,
            "7": self.show_google_accounts,
            "8": self.password_generator_menu,
            "9": self.sort_records_menu,
            "10": self.toggle_favorite,
            "11": self.exit_app,
            "12": self.show_statistics,
            "13": self.export_backup_menu,
            "14": self.import_backup_menu,
            "15": self.password_strength_checker,
        }
        action = actions.get(choice)
        if action is None:
            print("Invalid Option! Please choose a number from 1 to 15.")
            return
        action()
    # ------------------------------------------------------------------
    # Feature: Save New Record
    # ------------------------------------------------------------------
    def save_new_record(self) -> None:
        """Collect input and save a new password record."""
        utils.print_header("SAVE NEW RECORD")
        title = utils.prompt_required("Title")
        category = self._choose_category()
        print("\nLogin Method:")
        print("1. Custom Credentials")
        print("2. Google Linked")
        method = input("Choose an option (1-2): ").strip()
        if method == "2":
            record = self._build_google_linked_record(title, category)
        else:
            record = self._build_custom_record(title, category)
        if record is not None:
            self.manager.add_record(record)
            print(f"\n'{record.title}' has been saved successfully.")
    def _choose_category(self) -> str:
        """Display category options and return the user's selection.
        Returns:
            str: The chosen category name.
        """
        print("\nCategory:")
        for i, category in enumerate(CATEGORIES, start=1):
            print(f"{i}. {category}")
        while True:
            raw = input(f"Choose a category (1-{len(CATEGORIES)}): ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(CATEGORIES):
                return CATEGORIES[int(raw) - 1]
            print(f"Please enter a number between 1 and {len(CATEGORIES)}.")
    def _build_custom_record(self, title: str, category: str) -> PasswordRecord:
        """Collect custom-credential fields and build a PasswordRecord.
        Args:
            title (str): The record's title.
            category (str): The record's category.
        Returns:
            PasswordRecord: A new record with login_type "custom".
        """
        print("\n--- Custom Credentials ---")
        username = utils.prompt_optional("Username")
        email = utils.prompt_email("Email", required=True)
        phone = utils.prompt_optional("Phone Number")
        password = self._prompt_password_with_generator_option()
        website = utils.prompt_optional("Website")
        notes = utils.prompt_optional("Notes")
        favorite = utils.prompt_yes_no("Favorite?", default=False)
        return PasswordRecord(
            title=title,
            category=category,
            login_type="custom",
            username=username,
            email=email,
            phone=phone,
            password=password,
            website=website,
            notes=notes,
            favorite=favorite,
        )
    def _prompt_password_with_generator_option(self) -> str:
        """Prompt for a password, offering to generate one securely.
        Returns:
            str: The final password chosen or generated by the user.
        """
        use_generator = utils.prompt_yes_no(
            "Would you like to generate a secure password instead of typing one?",
            default=False,
        )
        if use_generator:
            return self._run_password_generator(return_only=True)
        return utils.prompt_required("Password")
    def _build_google_linked_record(self, title: str, category: str) -> Optional[PasswordRecord]:
        """Collect Google-linked fields and build a PasswordRecord.
        Args:
            title (str): The record's title.
            category (str): The record's category.
        Returns:
            Optional[PasswordRecord]: A new record with login_type
            "google", or None if no Google accounts are available.
        """
        if not self.manager.google_accounts:
            print(
                "\nNo Google accounts found. Please add one first "
                "(Main Menu > Add Google Account)."
            )
            return None
        print("\n--- Select a Google Account ---")
        for i, account in enumerate(self.manager.google_accounts, start=1):
            print(f"{i}. {account.email}")
        index = utils.prompt_int("Choose an account number", minimum=1, maximum=len(self.manager.google_accounts))
        account = self.manager.get_google_account_by_index(index)
        website = utils.prompt_optional("Website")
        notes = utils.prompt_optional("Notes")
        favorite = utils.prompt_yes_no("Favorite?", default=False)
        return PasswordRecord(
            title=title,
            category=category,
            login_type="google",
            google_email=account.email,
            website=website,
            notes=notes,
            favorite=favorite,
        )
    # ------------------------------------------------------------------
    # Feature: Show All Records
    # ------------------------------------------------------------------
    def show_all_records(self) -> None:
        """Display all record titles, then show details for a chosen one."""
        utils.print_header("ALL RECORDS")
        if not self.manager.records:
            print("No records saved yet.")
            return
        self._list_records(self.manager.records)
        self._prompt_and_show_detail(self.manager.records)
    def _list_records(self, records: List[PasswordRecord]) -> None:
        """Print a numbered list of record titles with quick context.
        Args:
            records (List[PasswordRecord]): Records to display.
        """
        for i, record in enumerate(records, start=1):
            star = "★ " if record.favorite else ""
            print(f"{i}. {star}{record.title}  [{record.category}]")
    def _prompt_and_show_detail(self, records: List[PasswordRecord]) -> None:
        """Ask the user to pick a record from a list and show its details.
        Args:
            records (List[PasswordRecord]): The list currently displayed,
                so the index typed by the user maps correctly.
        """
        if not records:
            return
        raw = input(
            "\nEnter a number to view details (or press Enter to go back): "
        ).strip()
        if not raw:
            return
        if not raw.isdigit() or not (1 <= int(raw) <= len(records)):
            print("Invalid Record Number!")
            return
        self._display_record_detail(records[int(raw) - 1])
    def _display_record_detail(self, record: PasswordRecord) -> None:
        """Pretty-print every field of a single record.
        Args:
            record (PasswordRecord): The record to display.
        """
        utils.print_header(record.title)
        print(f"Category     : {record.category}")
        print(f"Login Type   : {record.login_type.capitalize()}")
        if record.login_type == "google":
            print(f"Google Email : {record.google_email}")
        else:
            print(f"Username     : {record.username or '-'}")
            print(f"Email        : {record.email or '-'}")
            print(f"Phone        : {record.phone or '-'}")
            print(f"Password     : {record.password}")
            print(f"Strength     : {utils.check_password_strength(record.password)}")
        print(f"Website      : {record.website or '-'}")
        print(f"Notes        : {record.notes or '-'}")
        print(f"Favorite     : {'Yes' if record.favorite else 'No'}")
        print(f"Created At   : {record.created_at}")
        print(f"Updated At   : {record.updated_at}")
        utils.print_divider()
    # ------------------------------------------------------------------
    # Feature: Search Records
    # ------------------------------------------------------------------
    def search_records(self) -> None:
        """Search records by title, category, email, or website."""
        utils.print_header("SEARCH RECORDS")
        query = utils.prompt_optional("Search term")
        if not query:
            print("Search term cannot be empty.")
            return
        results = self.manager.search_records(query)
        if not results:
            print(f"No Records Matched '{query}'.")
            return
        print(f"\nFound {len(results)} matching record(s):")
        self._list_records(results)
        self._prompt_and_show_detail(results)
    # ------------------------------------------------------------------
    # Feature: Edit Record
    # ------------------------------------------------------------------
    def edit_record(self) -> None:
        """Edit an existing record, leaving fields blank to keep old values."""
        utils.print_header("EDIT RECORD")
        if not self.manager.records:
            print("No Records to Edit.")
            return
        self._list_records(self.manager.records)
        index = utils.prompt_int(
            "Enter the number of the record to edit",
            minimum=1,
            maximum=len(self.manager.records),
        )
        record = self.manager.get_record_by_index(index)
        if record is None:
            print("Invalid Record Number.")
            return
        print(f"\nEditing '{record.title}'. Press Enter to keep the current value.")
        record.title = self._edit_text_field("Title", record.title)
        record.category = self._edit_category_field(record.category)
        if record.login_type == "custom":
            record.username = self._edit_text_field("Username", record.username)
            record.email = self._edit_email_field("Email", record.email)
            record.phone = self._edit_text_field("Phone Number", record.phone)
            record.password = self._edit_text_field("Password", record.password)
        else:
            record.google_email = self._edit_google_email_field(record.google_email)
        record.website = self._edit_text_field("Website", record.website)
        record.notes = self._edit_text_field("Notes", record.notes)
        change_favorite = utils.prompt_yes_no(
            f"Favorite is currently '{record.favorite}'. Toggle it?", default=False
        )
        if change_favorite:
            record.favorite = not record.favorite
        self.manager.update_record(record)
        print(f"\n✓ '{record.title}' has been updated.")
    def _edit_text_field(self, label: str, current_value: str) -> str:
        """Prompt to edit a plain text field, keeping the old value if blank.
        Args:
            label (str): Field name to show in the prompt.
            current_value (str): Current value of the field.
        Returns:
            str: The new value, or the unchanged current value.
        """
        new_value = input(f"{label} [{current_value or '-'}]: ").strip()
        return new_value if new_value else current_value
    def _edit_email_field(self, label: str, current_value: str) -> str:
        """Prompt to edit an email field with validation.
        Args:
            label (str): Field name to show in the prompt.
            current_value (str): Current value of the field.
        Returns:
            str: A validated new email, or the unchanged current value.
        """
        while True:
            new_value = input(f"{label} [{current_value or '-'}]: ").strip()
            if not new_value:
                return current_value
            if utils.is_valid_email(new_value):
                return new_value
            print("That doesn't look like a valid email address. Try again.")
    def _edit_category_field(self, current_value: str) -> str:
        """Prompt to optionally change the record's category.
        Args:
            current_value (str): Current category value.
        Returns:
            str: The new category, or the unchanged current value.
        """
        change = utils.prompt_yes_no(
            f"Category is currently '{current_value}'. Change it?", default=False
        )
        if not change:
            return current_value
        return self._choose_category()
    def _edit_google_email_field(self, current_value: str) -> str:
        """Prompt to optionally change which Google account is linked.
        Args:
            current_value (str): Current linked Google email.
        Returns:
            str: The new linked email, or the unchanged current value.
        """
        if not self.manager.google_accounts:
            return current_value
        change = utils.prompt_yes_no(
            f"Linked Google account is currently '{current_value}'. Change it?",
            default=False,
        )
        if not change:
            return current_value
        for i, account in enumerate(self.manager.google_accounts, start=1):
            print(f"{i}. {account.email}")
        index = utils.prompt_int(
            "Choose an account number", minimum=1, maximum=len(self.manager.google_accounts)
        )
        account = self.manager.get_google_account_by_index(index)
        return account.email if account else current_value
    # ------------------------------------------------------------------
    # Feature: Delete Record
    # ------------------------------------------------------------------
    def delete_record(self) -> None:
        """Delete a record after confirming with the user."""
        utils.print_header("DELETE RECORD")
        if not self.manager.records:
            print("No records to delete.")
            return
        self._list_records(self.manager.records)
        index = utils.prompt_int(
            "Enter the number of the record to delete",
            minimum=1,
            maximum=len(self.manager.records),
        )
        record = self.manager.get_record_by_index(index)
        if record is None:
            print("Invalid Record Number.")
            return

        confirmed = utils.prompt_yes_no(
            f"Are you sure you want to delete '{record.title}'? This cannot be undone.",
            default=False,
        )
        if confirmed:
            self.manager.delete_record(record)
            print(f"'{record.title}' has been deleted.")
        else:
            print("Deletion cancelled.")

    # ------------------------------------------------------------------
    # Feature: Google Account Management
    # ------------------------------------------------------------------

    def add_google_account(self) -> None:
        """Add a new Google account, preventing duplicate emails."""
        utils.print_header("ADD GOOGLE ACCOUNT")
        email = utils.prompt_email("Google Email", required=True)

        if self.manager.find_google_account(email) is not None:
            print(f"The account '{email}' already exists.")
            return

        account = self.manager.add_google_account(email)
        if account:
            print(f"Google account '{email}' has been added.")

    def show_google_accounts(self) -> None:
        """Display all stored Google accounts."""
        utils.print_header("GOOGLE ACCOUNTS")
        if not self.manager.google_accounts:
            print("No Google accounts saved yet.")
            return
        for i, account in enumerate(self.manager.google_accounts, start=1):
            print(f"{i}. {account.email}  (added {account.created_at})")

    # ------------------------------------------------------------------
    # Feature: Password Generator
    # ------------------------------------------------------------------

    def password_generator_menu(self) -> None:
        """Interactive password generator menu (standalone use)."""
        self._run_password_generator(return_only=False)

    def _run_password_generator(self, return_only: bool) -> str:
        """Run the password generator flow and optionally print results.

        Args:
            return_only (bool): If True, suppress extra menu framing
                because this is being called from within another flow
                (e.g. while creating a new record).

        Returns:
            str: The generated password.
        """
        if not return_only:
            utils.print_header("PASSWORD GENERATOR")

        length = utils.prompt_int("Password length", minimum=4, maximum=128)
        use_numbers = utils.prompt_yes_no("Include numbers?", default=True)
        use_symbols = utils.prompt_yes_no("Include symbols?", default=True)
        use_uppercase = utils.prompt_yes_no("Include uppercase letters?", default=True)
        use_lowercase = utils.prompt_yes_no("Include lowercase letters?", default=True)

        try:
            password = utils.generate_password(
                length=length,
                use_numbers=use_numbers,
                use_symbols=use_symbols,
                use_uppercase=use_uppercase,
                use_lowercase=use_lowercase,
            )
        except ValueError as exc:
            print(f"{exc} Defaulting to lowercase + numbers.")
            password = utils.generate_password(
                length=length, use_numbers=True, use_symbols=False,
                use_uppercase=False, use_lowercase=True,
            )

        strength = utils.check_password_strength(password)
        print(f"\nGenerated Password : {password}")
        print(f"Strength           : {strength}")

        if utils.prompt_yes_no("Copy this password to clipboard?", default=False):
            self._copy_with_feedback(password)

        return password

    # ------------------------------------------------------------------
    # Feature: Sort Records
    # ------------------------------------------------------------------

    def sort_records_menu(self) -> None:
        """Display records sorted by a user-chosen key."""
        utils.print_header("SORT RECORDS")
        if not self.manager.records:
            print("No records to sort.")
            return

        print("Sort by:")
        print("1. Title")
        print("2. Category")
        print("3. Newest")
        print("4. Oldest")
        print("5. Favorites First")

        key_map = {
            "1": "title",
            "2": "category",
            "3": "newest",
            "4": "oldest",
            "5": "favorites",
        }
        choice = input("Choose an option (1-5): ").strip()
        key = key_map.get(choice)
        if key is None:
            print("Invalid Option.")
            return

        sorted_records = self.manager.sort_records(key)
        self._list_records(sorted_records)
        self._prompt_and_show_detail(sorted_records)

    # ------------------------------------------------------------------
    # Feature: Toggle Favorite
    # ------------------------------------------------------------------

    def toggle_favorite(self) -> None:
        """Toggle the favorite flag on a chosen record."""
        utils.print_header("TOGGLE FAVORITE")
        if not self.manager.records:
            print("No records available.")
            return

        self._list_records(self.manager.records)
        index = utils.prompt_int(
            "Enter the number of the record to toggle",
            minimum=1,
            maximum=len(self.manager.records),
        )
        record = self.manager.get_record_by_index(index)
        if record is None:
            print("Invalid Record Number.")
            return

        self.manager.toggle_favorite(record)
        status = "marked as favorite" if record.favorite else "removed from favorites"
        print(f"'{record.title}' has been {status}.")

    # ------------------------------------------------------------------
    # Feature: Copy Password to Clipboard (used by Password Generator)
    # ------------------------------------------------------------------

    def _copy_with_feedback(self, text: str) -> None:
        """Attempt to copy text to clipboard and report the outcome.
        Args:
            text (str): The text to copy.
        """
        success = utils.copy_to_clipboard(text)
        if success:
            print("Password copied to clipboard.")
        else:
            print(
                "Could not copy to clipboard (pyperclip/clipboard backend "
                "unavailable in this environment)."
            )

    # ------------------------------------------------------------------
    # Bonus Feature: Statistics
    # ------------------------------------------------------------------

    def show_statistics(self) -> None:
        """Display summary statistics about stored data."""
        utils.print_header("STATISTICS")
        stats = self.manager.get_statistics()
        print(f"Total Passwords          : {stats['total_passwords']}")
        print(f"Favorite Passwords       : {stats['favorite_passwords']}")
        print(f"Google Linked Accounts   : {stats['google_linked_accounts']}")
        print(f"Custom Accounts          : {stats['custom_accounts']}")
        print(f"Saved Google Accounts    : {stats['saved_google_accounts']}")

    # ------------------------------------------------------------------
    # Bonus Feature: Export / Import Backup
    # ------------------------------------------------------------------

    def export_backup_menu(self) -> None:
        """Export all data to a backup JSON file chosen by the user."""
        utils.print_header("EXPORT BACKUP")
        default_name = "backup.json"
        raw = input(f"Backup file name [{default_name}]: ").strip()
        backup_path = raw if raw else default_name

        try:
            self.manager.export_backup(backup_path)
            print(f"Backup successfully exported to '{backup_path}'.")
        except StorageError as exc:
            print(f"✗ {exc}")

    def import_backup_menu(self) -> None:
        """Import data from a backup JSON file chosen by the user."""
        utils.print_header("IMPORT BACKUP")
        backup_path = utils.prompt_required("Backup file path")

        merge = utils.prompt_yes_no(
            "Merge with existing data? (No will replace all current data)",
            default=False,
        )

        if not merge:
            confirmed = utils.prompt_yes_no(
                "This will REPLACE all current records and Google accounts. Continue?",
                default=False,
            )
            if not confirmed:
                print("Import cancelled.")
                return

        try:
            count = self.manager.import_backup(backup_path, merge=merge)
            print(f"Imported {count} record(s) from '{backup_path}'.")
        except StorageError as exc:
            print(f"✗ {exc}")

    # ------------------------------------------------------------------
    # Bonus Feature: Standalone Password Strength Checker
    # ------------------------------------------------------------------

    def password_strength_checker(self) -> None:
        """Check the strength of an arbitrary, user-supplied password."""
        utils.print_header("PASSWORD STRENGTH CHECKER")
        password = utils.prompt_required("Enter a password to check")
        strength = utils.check_password_strength(password)
        print(f"Strength: {strength}")

    # ------------------------------------------------------------------
    # Feature: Exit
    # ------------------------------------------------------------------

    def exit_app(self) -> None:
        """Print a goodbye message and exit the application."""
        print("\nGoodbye! Your data has been saved.")
        sys.exit(0)


def main() -> None:
    """Application entry point.
    Creates the PasswordManager instance and starts the console UI.
    Handles startup-level storage errors gracefully.
    """
    try:
        manager = PasswordManager(STORAGE_FILE)
    except StorageError as exc:
        print(f"Fatal storage error during startup: {exc}")
        sys.exit(1)
    app = PasswordManagerApp(manager)
    app.run()
if __name__ == "__main__":
    main()