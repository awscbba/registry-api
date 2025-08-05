#!/usr/bin/env python3
"""
Systematic Production Risk Fix Tool

This tool automatically fixes the high-risk production issues identified
by the analyze_production_risks.py script.
"""

import json
import re
from pathlib import Path
from typing import List, Dict

class ProductionRiskFixer:
    def __init__(self):
        self.fixes_applied = []
        
    def load_risks(self) -> Dict:
        """Load the risk analysis results"""
        with open("production_risks.json", "r") as f:
            return json.load(f)
    
    def fix_high_risk_issues(self):
        """Fix all high-risk issues automatically"""
        print("🔧 Starting systematic fix of HIGH RISK production issues...")
        
        risks = self.load_risks()
        
        # Fix DynamoDB parameter issues
        self.fix_dynamodb_parameter_issues(risks.get("dynamodb_parameter_issues", []))
        
        # Fix async/await mismatches
        self.fix_async_await_issues(risks.get("async_await_mismatches", []))
        
        print(f"\n✅ Applied {len(self.fixes_applied)} fixes!")
        return self.fixes_applied
    
    def fix_dynamodb_parameter_issues(self, issues: List[Dict]):
        """Fix DynamoDB ExpressionAttributeNames issues"""
        print("📊 Fixing DynamoDB parameter issues...")
        
        for issue in issues:
            if issue["risk"] != "HIGH":
                continue
                
            file_path = Path(issue["file"])
            if not file_path.exists():
                continue
                
            print(f"  🔧 Fixing {file_path}:{issue['line']}")
            
            # Read file content
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Find the problematic line
            line_idx = issue["line"] - 1
            if line_idx >= len(lines):
                continue
                
            original_line = lines[line_idx]
            
            # Check if this is the old DynamoDB service (we already fixed DefensiveDynamoDBService)
            if "dynamodb_service.py" in str(file_path):
                # This is the old service - we should apply the same fix pattern
                if "ExpressionAttributeNames=expression_names if expression_names else None" in original_line:
                    # Find the update_item call context
                    context_start = max(0, line_idx - 10)
                    context_end = min(len(lines), line_idx + 5)
                    
                    # Look for the update_item call
                    for i in range(context_start, context_end):
                        if "update_item(" in lines[i]:
                            # Apply the conditional parameter fix
                            self.apply_conditional_parameter_fix(file_path, lines, i, line_idx)
                            break
    
    def apply_conditional_parameter_fix(self, file_path: Path, lines: List[str], update_item_line: int, expression_names_line: int):
        """Apply the conditional parameter building fix"""
        # Find the method that contains this update_item call
        method_start = None
        for i in range(update_item_line - 20, update_item_line):
            if i >= 0 and ("def " in lines[i] and "update_" in lines[i]):
                method_start = i
                break
        
        if method_start is None:
            return
            
        # Extract the update_item call
        update_call_lines = []
        brace_count = 0
        in_call = False
        
        for i in range(update_item_line, min(len(lines), update_item_line + 10)):
            line = lines[i]
            if "update_item(" in line:
                in_call = True
            
            if in_call:
                update_call_lines.append((i, line))
                brace_count += line.count('(') - line.count(')')
                if brace_count <= 0 and ')' in line:
                    break
        
        if not update_call_lines:
            return
            
        # Build the new conditional parameter version
        new_lines = []
        
        # Add the conditional parameter building
        indent = "        "  # Assume 8 spaces
        new_lines.extend([
            f"{indent}# Build update parameters",
            f"{indent}update_params = {{",
            f"{indent}    \"Key\": {{\"id\": item_id}},",
            f"{indent}    \"UpdateExpression\": update_expression,",
            f"{indent}    \"ExpressionAttributeValues\": expression_values,",
            f"{indent}    \"ReturnValues\": \"ALL_NEW\",",
            f"{indent}}}",
            f"{indent}",
            f"{indent}# Only add ExpressionAttributeNames if it's not empty",
            f"{indent}if expression_names:",
            f"{indent}    update_params[\"ExpressionAttributeNames\"] = expression_names",
            f"{indent}",
            f"{indent}response = table.update_item(**update_params)"
        ])
        
        # Replace the original update_item call
        start_line = update_call_lines[0][0]
        end_line = update_call_lines[-1][0]
        
        # Replace the lines
        new_content_lines = lines[:start_line] + new_lines + lines[end_line + 1:]
        
        # Write back to file
        file_path.write_text('\n'.join(new_content_lines))
        
        self.fixes_applied.append({
            "file": str(file_path),
            "type": "dynamodb_conditional_parameters",
            "lines": f"{start_line}-{end_line}",
            "description": "Applied conditional parameter building for DynamoDB update_item"
        })
    
    def fix_async_await_issues(self, issues: List[Dict]):
        """Fix missing await keywords for async methods"""
        print("⚡ Fixing async/await issues...")
        
        for issue in issues:
            if issue["risk"] != "HIGH":
                continue
                
            file_path = Path(issue["file"])
            if not file_path.exists():
                continue
                
            print(f"  🔧 Fixing {file_path}:{issue['line']}")
            
            # Read file content
            content = file_path.read_text()
            lines = content.split('\n')
            
            # Find the problematic line
            line_idx = issue["line"] - 1
            if line_idx >= len(lines):
                continue
                
            original_line = lines[line_idx]
            
            # Add await keyword if missing
            if "db_service." in original_line and "await" not in original_line:
                # Find the assignment pattern
                if " = " in original_line:
                    parts = original_line.split(" = ", 1)
                    if len(parts) == 2:
                        left_part = parts[0]
                        right_part = parts[1]
                        
                        # Add await to the right part
                        if "db_service." in right_part:
                            new_line = f"{left_part} = await {right_part}"
                            lines[line_idx] = new_line
                            
                            # Write back to file
                            file_path.write_text('\n'.join(lines))
                            
                            self.fixes_applied.append({
                                "file": str(file_path),
                                "type": "missing_await",
                                "line": issue["line"],
                                "description": f"Added await keyword for async method call",
                                "before": original_line.strip(),
                                "after": new_line.strip()
                            })
    
    def generate_fix_report(self) -> str:
        """Generate a report of all fixes applied"""
        report = []
        report.append("# Production Risk Fixes Applied")
        report.append("=" * 50)
        report.append("")
        
        if not self.fixes_applied:
            report.append("No fixes were applied.")
            return "\n".join(report)
        
        report.append(f"## Summary")
        report.append(f"- **Total Fixes Applied**: {len(self.fixes_applied)}")
        report.append("")
        
        # Group by type
        fixes_by_type = {}
        for fix in self.fixes_applied:
            fix_type = fix["type"]
            if fix_type not in fixes_by_type:
                fixes_by_type[fix_type] = []
            fixes_by_type[fix_type].append(fix)
        
        for fix_type, fixes in fixes_by_type.items():
            report.append(f"## {fix_type.replace('_', ' ').title()}")
            report.append(f"Applied {len(fixes)} fixes:")
            report.append("")
            
            for fix in fixes:
                report.append(f"### {fix['file']}:{fix.get('line', fix.get('lines', ''))}")
                report.append(f"- **Description**: {fix['description']}")
                if 'before' in fix and 'after' in fix:
                    report.append(f"- **Before**: `{fix['before']}`")
                    report.append(f"- **After**: `{fix['after']}`")
                report.append("")
        
        return "\n".join(report)

def main():
    fixer = ProductionRiskFixer()
    
    # Check if risk analysis exists
    if not Path("production_risks.json").exists():
        print("❌ No risk analysis found. Run analyze_production_risks.py first.")
        return
    
    # Apply fixes
    fixes = fixer.fix_high_risk_issues()
    
    # Generate report
    report = fixer.generate_fix_report()
    
    # Save report
    with open("PRODUCTION_FIXES_APPLIED.md", "w") as f:
        f.write(report)
    
    print(f"\n📄 Fix report saved to: PRODUCTION_FIXES_APPLIED.md")
    
    if fixes:
        print("🎯 High-risk issues have been systematically fixed!")
        print("🧪 Run tests to verify the fixes work correctly.")
    else:
        print("✅ No high-risk issues found to fix.")

if __name__ == "__main__":
    main()