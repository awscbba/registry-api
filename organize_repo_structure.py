#!/usr/bin/env python3
"""
Repository Organization Tool

This tool helps organize the repository structure by:
1. Identifying documentation that should be moved to registry-documentation
2. Identifying scripts that should be organized properly
3. Cleaning up temporary/debug files
4. Creating a proper project structure
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict


class RepoOrganizer:
    def __init__(self):
        self.current_dir = Path(".")
        self.actions = []

    def analyze_current_structure(self) -> Dict[str, List[str]]:
        """Analyze current repository structure"""
        structure = {
            "documentation": [],
            "analysis_scripts": [],
            "debug_scripts": [],
            "test_scripts": [],
            "temporary_files": [],
            "core_files": [],
        }

        for item in self.current_dir.iterdir():
            if item.is_file():
                name = item.name

                # Documentation files
                if name.endswith(".md") and name not in ["README.md"]:
                    structure["documentation"].append(name)

                # Analysis and production tools
                elif (
                    name.startswith("analyze_")
                    or name.startswith("fix_")
                    or "production" in name.lower()
                ):
                    if name.endswith(".py"):
                        structure["analysis_scripts"].append(name)
                    elif name.endswith(".md") or name.endswith(".json"):
                        structure["documentation"].append(name)

                # Debug and test scripts
                elif (
                    name.startswith("debug_")
                    or name.startswith("test_")
                    or name.startswith("run_")
                ):
                    structure["debug_scripts"].append(name)

                # Temporary or one-off files
                elif name.startswith("demo_") or name.startswith("apply_"):
                    structure["temporary_files"].append(name)

                # Core project files
                elif name in [
                    "pyproject.toml",
                    "requirements.txt",
                    "requirements-lambda.txt",
                    "justfile",
                    "README.md",
                    "main.py",
                    "main_versioned.py",
                    "router_main.py",
                    "conftest.py",
                    "uv.lock",
                    ".envrc",
                    ".flake8",
                    ".gitignore",
                    ".python-version",
                ]:
                    structure["core_files"].append(name)

        return structure

    def create_organization_plan(self) -> Dict[str, str]:
        """Create a plan for organizing the repository"""
        structure = self.analyze_current_structure()

        plan = {
            "actions": {
                "move_to_docs": {
                    "description": "Move to registry-documentation repo",
                    "files": structure["documentation"],
                    "reason": "Documentation should be centralized in the docs repo",
                },
                "create_scripts_dir": {
                    "description": "Create scripts/ directory for analysis tools",
                    "files": structure["analysis_scripts"],
                    "reason": "Analysis and production tools should be organized in scripts/",
                },
                "create_debug_dir": {
                    "description": "Create debug/ directory for debug scripts",
                    "files": structure["debug_scripts"],
                    "reason": "Debug and test scripts should be organized separately",
                },
                "remove_temporary": {
                    "description": "Remove temporary files",
                    "files": structure["temporary_files"],
                    "reason": "These are one-off files that are no longer needed",
                },
                "keep_core": {
                    "description": "Keep in root",
                    "files": structure["core_files"],
                    "reason": "Core project files should remain in root",
                },
            }
        }

        return plan

    def generate_organization_report(self) -> str:
        """Generate a report of the organization plan"""
        plan = self.create_organization_plan()

        report = []
        report.append("# Repository Organization Plan")
        report.append("=" * 50)
        report.append("")

        report.append("## Current Repository Analysis")
        report.append("")

        for action_name, action_info in plan["actions"].items():
            if not action_info["files"]:
                continue

            report.append(f"### {action_info['description']}")
            report.append(f"**Reason**: {action_info['reason']}")
            report.append("")
            report.append("**Files:**")
            for file in action_info["files"]:
                report.append(f"- `{file}`")
            report.append("")

        report.append("## Recommended Actions")
        report.append("")

        # Documentation move
        doc_files = plan["actions"]["move_to_docs"]["files"]
        if doc_files:
            report.append("### 1. Move Documentation to registry-documentation")
            report.append("```bash")
            report.append("# In registry-documentation repo:")
            report.append("mkdir -p production-analysis")
            for file in doc_files:
                if "PRODUCTION" in file or "production" in file:
                    report.append(f"# Move {file} to production-analysis/")
                else:
                    report.append(f"# Move {file} to appropriate docs section")
            report.append("```")
            report.append("")

        # Scripts organization
        script_files = plan["actions"]["create_scripts_dir"]["files"]
        if script_files:
            report.append("### 2. Organize Analysis Scripts")
            report.append("```bash")
            report.append("mkdir -p scripts/production-analysis")
            for file in script_files:
                report.append(f"mv {file} scripts/production-analysis/")
            report.append("```")
            report.append("")

        # Debug scripts
        debug_files = plan["actions"]["create_debug_dir"]["files"]
        if debug_files:
            report.append("### 3. Organize Debug Scripts")
            report.append("```bash")
            report.append("mkdir -p debug/")
            for file in debug_files:
                report.append(f"mv {file} debug/")
            report.append("```")
            report.append("")

        # Cleanup
        temp_files = plan["actions"]["remove_temporary"]["files"]
        if temp_files:
            report.append("### 4. Clean Up Temporary Files")
            report.append("```bash")
            for file in temp_files:
                report.append(f"rm {file}  # One-off script, no longer needed")
            report.append("```")
            report.append("")

        report.append("## Final Repository Structure")
        report.append("```")
        report.append("registry-api/")
        report.append("├── src/                    # Source code")
        report.append("├── tests/                  # Test files")
        report.append("├── scripts/                # Analysis and production tools")
        report.append("│   └── production-analysis/")
        report.append("├── debug/                  # Debug and development scripts")
        report.append("├── .codecatalyst/          # CI/CD configuration")
        report.append("├── .devbox/               # Development environment")
        report.append("├── pyproject.toml         # Project configuration")
        report.append("├── justfile               # Task runner")
        report.append("├── README.md              # Project overview")
        report.append("└── main*.py               # Entry points")
        report.append("```")
        report.append("")

        report.append("## Benefits")
        report.append("- **Cleaner root directory**: Only essential files in root")
        report.append("- **Better organization**: Scripts grouped by purpose")
        report.append(
            "- **Documentation centralized**: All docs in registry-documentation"
        )
        report.append("- **Easier maintenance**: Clear separation of concerns")
        report.append("- **Better CI/CD**: Cleaner repository for pipeline processing")

        return "\n".join(report)

    def should_keep_analysis_scripts(self) -> bool:
        """Determine if analysis scripts should be kept in the live repo"""
        # These are valuable production tools that should be available in the live repo
        # for debugging production issues
        return True


def main():
    organizer = RepoOrganizer()

    # Generate organization report
    report = organizer.generate_organization_report()

    # Save report
    with open("REPOSITORY_ORGANIZATION_PLAN.md", "w") as f:
        f.write(report)

    print("📋 Repository Organization Plan")
    print("=" * 40)
    print("📄 Plan saved to: REPOSITORY_ORGANIZATION_PLAN.md")
    print("")
    print("🤔 Key Questions to Consider:")
    print("1. Should analysis scripts stay in live repo for production debugging?")
    print("2. Which documentation should move to registry-documentation?")
    print("3. Should we keep debug scripts or remove them?")
    print("")
    print("💡 Recommendation:")
    print("- Keep production analysis tools in scripts/ for debugging")
    print("- Move comprehensive documentation to registry-documentation")
    print("- Organize debug scripts in debug/ folder")
    print("- Clean up temporary one-off files")


if __name__ == "__main__":
    main()
