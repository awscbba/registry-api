#!/usr/bin/env python3
"""
Script to apply standardized components (error handling, logging, response models)
across all handler files in the API project.
"""

import os
import re
from pathlib import Path


def update_handler_imports(file_path: Path) -> bool:
    """Update imports in a handler file to include standardized components."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Skip if already updated
        if "from ..utils.error_handler import" in content:
            print(f"✓ {file_path.name} already has standardized imports")
            return False

        # Skip if it's the versioned_api_handler (already updated)
        if "versioned_api_handler.py" in str(file_path):
            return False

        original_content = content

        # Replace old logging import with standardized logging
        if (
            "import logging" in content
            and "logger = logging.getLogger(__name__)" in content
        ):
            # Add standardized imports after existing imports
            import_section_end = content.rfind("from ..")
            if import_section_end == -1:
                import_section_end = content.rfind("import ")

            if import_section_end != -1:
                # Find the end of the import line
                next_newline = content.find("\n", import_section_end)
                if next_newline != -1:
                    insert_point = next_newline + 1

                    # Add standardized imports
                    new_imports = """from ..utils.error_handler import StandardErrorHandler, handle_database_error, handle_authentication_error
from ..utils.logging_config import get_handler_logger
from ..utils.response_models import ResponseFactory

"""
                    content = (
                        content[:insert_point] + new_imports + content[insert_point:]
                    )

                    # Replace logger initialization
                    handler_name = file_path.stem.replace("_handler", "").replace(
                        "_", "_"
                    )
                    content = re.sub(
                        r"logger = logging\.getLogger\(__name__\)",
                        f'logger = get_handler_logger("{handler_name}")',
                        content,
                    )

                    # Remove old logging import if it's standalone
                    content = re.sub(
                        r"^import logging\n", "", content, flags=re.MULTILINE
                    )

        # Only write if content changed
        if content != original_content:
            with open(file_path, "w") as f:
                f.write(content)
            print(f"✓ Updated {file_path.name}")
            return True
        else:
            print(f"- No changes needed for {file_path.name}")
            return False

    except Exception as e:
        print(f"✗ Error updating {file_path.name}: {e}")
        return False


def update_error_patterns(file_path: Path) -> bool:
    """Update common error handling patterns in a handler file."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        original_content = content

        # Pattern 1: Database errors
        content = re.sub(
            r'logger\.error\(f"Error (getting|creating|updating|deleting) ([^"]+): \{str\(e\)\}"\)\s*raise HTTPException\(\s*status_code=status\.HTTP_500_INTERNAL_SERVER_ERROR,\s*detail="[^"]+",?\s*\)',
            r'raise handle_database_error("\1 \2", e)',
            content,
            flags=re.MULTILINE | re.DOTALL,
        )

        # Pattern 2: Authentication errors
        content = re.sub(
            r'logger\.error\(f"Login error: \{str\(e\)\}"\)\s*raise HTTPException\(\s*status_code=status\.HTTP_500_INTERNAL_SERVER_ERROR,\s*detail="Authentication failed",?\s*\)',
            r'logger.error("Authentication failed", operation="login", error_type=type(e).__name__)\n        raise handle_authentication_error("Authentication failed")',
            content,
            flags=re.MULTILINE | re.DOTALL,
        )

        # Only write if content changed
        if content != original_content:
            with open(file_path, "w") as f:
                f.write(content)
            print(f"✓ Updated error patterns in {file_path.name}")
            return True
        else:
            return False

    except Exception as e:
        print(f"✗ Error updating error patterns in {file_path.name}: {e}")
        return False


def main():
    """Apply standardized components to all handler files."""
    handlers_dir = Path(__file__).parent / "src" / "handlers"

    if not handlers_dir.exists():
        print(f"✗ Handlers directory not found: {handlers_dir}")
        return

    print("🔧 Applying standardized components to handler files...")
    print("=" * 60)

    updated_files = []

    # Process all Python files in handlers directory
    for handler_file in handlers_dir.glob("*.py"):
        if handler_file.name == "__init__.py":
            continue

        print(f"\n📁 Processing {handler_file.name}...")

        # Update imports
        imports_updated = update_handler_imports(handler_file)

        # Update error patterns
        patterns_updated = update_error_patterns(handler_file)

        if imports_updated or patterns_updated:
            updated_files.append(handler_file.name)

    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"✓ Processed {len(list(handlers_dir.glob('*.py'))) - 1} handler files")
    print(f"✓ Updated {len(updated_files)} files")

    if updated_files:
        print(f"\n📝 Updated files:")
        for file_name in updated_files:
            print(f"  - {file_name}")

        print(f"\n🚀 Next steps:")
        print(f"  1. Review the changes: git diff")
        print(f"  2. Run tests: python -m pytest tests/")
        print(f"  3. Run formatter: python -m black src/")
        print(f"  4. Run linter: python -m flake8 src/")
        print(
            f"  5. Commit changes: git add . && git commit -m 'feat: apply standardized components to all handlers'"
        )
    else:
        print("\n✨ All handlers already have standardized components!")


if __name__ == "__main__":
    main()
