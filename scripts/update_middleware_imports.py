#!/usr/bin/env python3
"""
Script to update handler imports from admin_middleware to admin_middleware_v2.
"""

import os
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_python_files(directory):
    """Find all Python files in the given directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files


def update_middleware_imports(file_path):
    """Update middleware imports in a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        changes_made = []

        # Pattern 1: from ..middleware.admin_middleware import
        pattern1 = r"from\s+\.\.middleware\.admin_middleware\s+import"
        replacement1 = "from ..middleware.admin_middleware_v2 import"
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            changes_made.append(
                "Updated relative import from admin_middleware to admin_middleware_v2"
            )

        # Pattern 2: from src.middleware.admin_middleware import
        pattern2 = r"from\s+src\.middleware\.admin_middleware\s+import"
        replacement2 = "from src.middleware.admin_middleware_v2 import"
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            changes_made.append(
                "Updated absolute import from admin_middleware to admin_middleware_v2"
            )

        # Pattern 3: import ..middleware.admin_middleware
        pattern3 = r"import\s+\.\.middleware\.admin_middleware"
        replacement3 = "import ..middleware.admin_middleware_v2"
        if re.search(pattern3, content):
            content = re.sub(pattern3, replacement3, content)
            changes_made.append("Updated relative module import")

        # Pattern 4: import src.middleware.admin_middleware
        pattern4 = r"import\s+src\.middleware\.admin_middleware"
        replacement4 = "import src.middleware.admin_middleware_v2"
        if re.search(pattern4, content):
            content = re.sub(pattern4, replacement4, content)
            changes_made.append("Updated absolute module import")

        # Write back if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return changes_made

        return []

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return []


def main():
    """Main function to update all handler files."""
    logger.info("🔄 Starting middleware import updates...")

    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    src_dir = os.path.join(project_root, "src")

    if not os.path.exists(src_dir):
        logger.error(f"❌ Source directory not found: {src_dir}")
        return

    # Find all Python files in src directory
    python_files = find_python_files(src_dir)
    logger.info(f"📁 Found {len(python_files)} Python files to check")

    # Track changes
    files_updated = 0
    total_changes = 0

    # Process each file
    for file_path in python_files:
        relative_path = os.path.relpath(file_path, project_root)
        changes = update_middleware_imports(file_path)

        if changes:
            files_updated += 1
            total_changes += len(changes)
            logger.info(f"✅ Updated {relative_path}:")
            for change in changes:
                logger.info(f"   - {change}")
        else:
            logger.debug(f"⏭️  No changes needed in {relative_path}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 MIDDLEWARE IMPORT UPDATE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"📁 Files checked: {len(python_files)}")
    logger.info(f"✅ Files updated: {files_updated}")
    logger.info(f"🔄 Total changes: {total_changes}")

    if files_updated > 0:
        logger.info("\n📋 NEXT STEPS:")
        logger.info("1. Review the changes made to ensure they're correct")
        logger.info("2. Run tests to verify everything still works")
        logger.info("3. Test admin endpoints with the new middleware")
        logger.info("4. Run: python scripts/verify_rbac_migration.py")
        logger.info("\n⚠️  IMPORTANT: Test thoroughly before deploying to production!")
    else:
        logger.info("\n✨ No files needed updating - all imports are already correct!")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
