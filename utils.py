"""
utils.py
========
Utility functions used across the Password Manager application.
This module contains stateless helper functions for:
- Input validation (emails, non-empty required fields, yes/no prompts).
- Secure password generation.
- Password strength evaluation.
- Clipboard interaction.
- Generic console input helpers that keep ``main.py`` clean and readable.
Keeping these functions separate from ``manager.py`` and ``main.py``
ensures a clear separation of concerns: utilities know nothing about the
data model or the menu flow, they just perform small, reusable tasks.
"""

from __future__ import annotations
import re
import secrets
import string
from typing import Optional

try:
    import pyperclip  # type: ignore
    _CLIPBOARD_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on environment
    _CLIPBOARD_AVAILABLE = False

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def is_valid_email(email: str) -> bool:
    """Validate an email address using a pragmatic regex check.
    Args:
        email (str): The email address to validate.
    Returns:
        bool: True if the email matches a basic valid pattern.
    """
    return bool(EMAIL_REGEX.match(email.strip()))

def is_non_empty(value: str) -> bool:
    """Check whether a string contains non-whitespace content.
    Args:
        value (str): The string to check.
    Returns:
        bool: True if the value has visible content.
    """
    return bool(value and value.strip())

def prompt_required(label: str) -> str:
    """Prompt the user for a required text field, re-asking until valid.
    Args:
        label (str): The field name to display in the prompt.
    Returns:
        str: A non-empty, stripped string supplied by the user.
    """
    while True:
        value = input(f"{label}: ").strip()
        if is_non_empty(value):
            return value
        print(f"{label} cannot be empty. Please try again.")

def prompt_optional(label: str) -> str:
    """Prompt the user for an optional text field.
    Args:
        label (str): The field name to display in the prompt.
    Returns:
        str: The stripped user input, or an empty string if left blank.
    """
    return input(f"{label} (optional): ").strip()

def prompt_email(label: str = "Email", required: bool = True) -> str:
    """Prompt for an email address and validate its format.
    Args:
        label (str): The field name to display in the prompt.
        required (bool): Whether the field must be filled in.
    Returns:
        str: A validated email address, or an empty string if optional
        and left blank.
    """
    while True:
        suffix = "" if required else " (optional)"
        value = input(f"{label}{suffix}: ").strip()
        if not value and not required:
            return ""
        if not value and required:
            print(f"{label} cannot be empty. Please try again.")
            continue
        if is_valid_email(value):
            return value
        print("That doesn't look like a valid email address. Try again.")

def prompt_yes_no(label: str, default: Optional[bool] = None) -> bool:
    """Prompt the user for a yes/no answer.
    Args:
        label (str): The question to display.
        default (Optional[bool]): Value returned if the user presses
            Enter without typing anything. If None, an empty response
            is rejected and the user is re-prompted.
    Returns:
        bool: True for yes, False for no.
    """
    if default is True:
        hint = " [Y/n]"
    elif default is False:
        hint = " [y/N]"
    else:
        hint = " (Y/N)"
    while True:
        value = input(f"{label}{hint}: ").strip().lower()
        if not value and default is not None:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("Please answer with 'y' or 'n'.")

def prompt_int(label: str, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    """Prompt the user for an integer within an optional range.
    Args:
        label (str): The field name to display in the prompt.
        minimum (Optional[int]): Minimum acceptable value (inclusive).
        maximum (Optional[int]): Maximum acceptable value (inclusive).
    Returns:
        int: A validated integer value.
    """
    while True:
        raw = input(f"{label}: ").strip()
        if not raw.lstrip("-").isdigit():
            print("Please enter a valid whole number.")
            continue
        value = int(raw)
        if minimum is not None and value < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be at most {maximum}.")
            continue
        return value

def generate_password(
    length: int = 16,
    use_numbers: bool = True,
    use_symbols: bool = True,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
) -> str:
    """Generate a cryptographically secure random password.
    Uses the ``secrets`` module rather than ``random`` to ensure the
    generated password is suitable for real security purposes.
    Args:
        length (int): Desired password length. Minimum enforced is 4.
        use_numbers (bool): Whether to include digit characters.
        use_symbols (bool): Whether to include punctuation symbols.
        use_uppercase (bool): Whether to include uppercase letters.
        use_lowercase (bool): Whether to include lowercase letters.
    Returns:
        str: A randomly generated password string.
    Raises:
        ValueError: If no character set is selected.
    """
    length = max(length, 4)
    pools = []
    if use_lowercase:
        pools.append(string.ascii_lowercase)
    if use_uppercase:
        pools.append(string.ascii_uppercase)
    if use_numbers:
        pools.append(string.digits)
    if use_symbols:
        pools.append("!@#$%^&*()-_=+[]{};:,.?")
    if not pools:
        raise ValueError("At least one character set must be selected.")
    # Guarantee at least one character from each selected pool.
    password_chars = [secrets.choice(pool) for pool in pools]
    all_chars = "".join(pools)
    remaining = length - len(password_chars)
    password_chars += [secrets.choice(all_chars) for _ in range(max(remaining, 0))]
    # Shuffle securely so the guaranteed characters aren't predictably placed.
    for i in range(len(password_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_chars[i], password_chars[j] = password_chars[j], password_chars[i]
    return "".join(password_chars[:length]) if len(password_chars) >= length else "".join(password_chars)

def check_password_strength(password: str) -> str:
    """Evaluate the strength of a password using simple heuristics.
    The score considers length, character variety (lowercase, uppercase,
    digits, symbols), and gives a qualitative rating.
    Args:
        password (str): The password to evaluate.
    Returns:
        str: One of "Very Weak", "Weak", "Moderate", "Strong", "Very Strong".
    """
    if not password:
        return "Very Weak"
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[^a-zA-Z0-9]", password):
        score += 1
    ratings = ["Very Weak", "Weak", "Moderate", "Strong", "Very Strong"]
    # Map the 0-7 score range onto the 5 rating buckets.
    index = min(score * len(ratings) // 8, len(ratings) - 1)
    return ratings[index]

def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard, if a clipboard backend is available.
    Args:
        text (str): The text to copy.
    Returns:
        bool: True if the copy operation succeeded, False otherwise
        (e.g. if ``pyperclip`` is not installed or no clipboard backend
        is available in the current environment).
    """
    if not _CLIPBOARD_AVAILABLE:
        return False
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        # pyperclip can raise platform-specific errors when no clipboard
        # mechanism (xclip/xsel/pbcopy/etc.) is available.
        return False

def print_header(title: str, width: int = 40) -> None:
    """Print a centered, decorated section header to the console.
    Args:
        title (str): The header text to display.
        width (int): Total width of the decorative line.
    """
    print("\n" + title.center(width, "="))

def print_divider(width: int = 40) -> None:
    """Print a simple horizontal divider line.
    Args:
        width (int): Length of the divider line.
    """
    print("-" * width)