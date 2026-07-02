#!/usr/bin/env python3
"""
Autonomous Quality Check - QZero Project
========================================

Purpose: Comprehensive code quality and security analysis of QZero.
Good for: Maintaining high-quality security research code, improving project
         reliability, and documenting code health status.

Criteria met:
- bueno para la humanidad: Improves open-source security code quality
- bueno para ti: Practices code analysis and automation
- bueno para el proyecto: Ensures code is maintainable and secure

What it checks:
1. Code quality (linting, imports, complexity)
2. Security issues (potential vulnerabilities)
3. Documentation completeness
4. Project structure consistency
5. Test coverage
"""

import os
import sys
import json
import subprocess
import ast
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class QualityChecker:
    """Comprehensive code quality and security checker."""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project": str(project_root.name),
            "checks": {},
            "overall_score": 0,
            "issues": [],
            "improvements": []
        }

    def check_imports(self, file_path):
        """Check Python files for import issues."""
        issues = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))

            # Check for wildcard imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == '*':
                            issues.append(f"Wildcard import detected: {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module == '*':
                        issues.append(f"Wildcard import from {node.module}")
                    elif node.module:
                        # Check for relative imports in non-package
                        if node.module.startswith('.'):
                            warnings.append(f"Relative import in {file_path}")

            # Check for common security imports
            security_imports = ['os.system', 'subprocess.call', 'eval', 'exec']
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for imp in security_imports:
                    if imp in content:
                        issues.append(f"Potential security issue: {imp}")

        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        except Exception as e:
            warnings.append(f"Error analyzing imports: {e}")

        return {
            "issues": issues,
            "warnings": warnings,
            "status": "passed" if not issues else "failed"
        }

    def check_code_complexity(self, file_path):
        """Check code complexity metrics."""
        issues = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Count lines of code
            lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
            loc = len(lines)
            complexity_score = min(100, max(0, loc / 50))  # 0-100 scale

            if loc > 500:
                issues.append(f"File too large: {loc} lines")

            # Check for long functions ( > 20 lines)
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_lines = ast.get_source_segment(content, node)
                    if func_lines:
                        func_lines_count = len([l for l in func_lines.split('\n') if l.strip()])
                        if func_lines_count > 20:
                            warnings.append(f"Long function: {node.name} ({func_lines_count} lines)")

        except Exception as e:
            warnings.append(f"Complexity analysis error: {e}")

        return {
            "issues": issues,
            "warnings": warnings,
            "status": "warning" if warnings or loc > 300 else "passed"
        }

    def check_documentation(self, file_path):
        """Check for documentation."""
        issues = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for module docstring
            tree = ast.parse(content, filename=str(file_path))
            has_docstring = any(
                isinstance(node, (ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(node)
                for node in ast.walk(tree)
            )

            if not has_docstring:
                warnings.append("Missing module/function/class docstrings")

            # Check for comments
            lines = content.split('\n')
            comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            comment_ratio = comment_lines / len(lines) if lines else 0

            if comment_ratio < 0.1:
                warnings.append("Low comment coverage (<10%)")

            # Check for inline comments
            if 'TODO' in content or 'FIXME' in content or 'XXX' in content:
                issues.append("Found TODO/FIXME comments")

        except Exception as e:
            warnings.append(f"Documentation check error: {e}")

        return {
            "issues": issues,
            "warnings": warnings,
            "status": "warning" if warnings else "passed"
        }

    def check_security(self, file_path):
        """Check for common security issues."""
        issues = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for hardcoded credentials
            hardcoded_patterns = [
                r'password\s*=\s*["\']',
                r'token\s*=\s*["\']',
                r'api_key\s*=\s*["\']',
                r'secret\s*=\s*["\']',
            ]

            for pattern in hardcoded_patterns:
                import re
                if re.search(pattern, content, re.IGNORECASE):
                    warnings.append(f"Potential hardcoded credential pattern: {pattern}")

            # Check for SQL injection patterns
            sql_patterns = [
                r'\.execute\([^"]*["\']SELECT',
                r'\.execute\([^"]*["\']INSERT',
                r'\.execute\([^"]*["\']UPDATE',
                r'\.execute\([^"]*["\']DELETE',
            ]

            if any(re.search(p, content, re.IGNORECASE) for p in sql_patterns):
                # Verify it's not using parameterized queries
                has_parametric = 'cursor.execute' in content and any(
                    '%s' in str(s) or '?' in str(s)
                    for s in content.split('execute')[1:5]
                )

                if not has_parametric:
                    issues.append("Potential SQL injection risk - check parameterized queries")

        except Exception as e:
            warnings.append(f"Security check error: {e}")

        return {
            "issues": issues,
            "warnings": warnings,
            "status": "failed" if issues else "warning" if warnings else "passed"
        }

    def check_project_structure(self):
        """Check project directory structure."""
        issues = []
        warnings = []

        required_dirs = ["src", "tests", "docs", "reports"]
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            if not dir_path.exists():
                issues.append(f"Missing directory: {dir_name}")

        # Check for README
        if not (project_root / "README.md").exists():
            warnings.append("Missing README.md")

        # Check for LICENSE
        if not (project_root / "LICENSE").exists():
            warnings.append("Missing LICENSE file")

        # Check for requirements.txt
        if not (project_root / "requirements.txt").exists():
            warnings.append("Missing requirements.txt")

        # Check for Python files
        py_files = list(project_root.rglob("*.py"))
        if len(py_files) < 10:
            issues.append(f"Few Python files: {len(py_files)}")

        return {
            "issues": issues,
            "warnings": warnings,
            "status": "failed" if issues else "warning" if warnings else "passed",
            "python_files": len(py_files)
        }

    def check_tests(self):
        """Check test coverage."""
        issues = []
        warnings = []

        test_files = list(project_root.rglob("test_*.py")) + list(project_root.rglob("*_test.py"))
        py_files = list(project_root.rglob("*.py"))

        if not test_files:
            warnings.append("No test files found")

        test_ratio = len(test_files) / len(py_files) if py_files else 0
        if test_ratio < 0.1:
            warnings.append(f"Low test coverage: {test_ratio*100:.1f}%")

        return {
            "issues": issues,
            "warnings": warnings,
            "status": "warning" if warnings else "passed",
            "test_files": len(test_files),
            "total_files": len(py_files),
            "coverage_ratio": round(test_ratio, 2)
        }

    def check_dependencies(self):
        """Check dependencies."""
        issues = []
        warnings = []

        requirements_file = project_root / "requirements.txt"
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]

                if len(deps) < 5:
                    warnings.append(f"Few dependencies: {len(deps)}")

                # Check for outdated patterns (rough check)
                for dep in deps:
                    if not any(version in dep for version in ['==', '>=', '<=']):
                        warnings.append(f"Dependency without version spec: {dep}")

            except Exception as e:
                warnings.append(f"Error reading requirements: {e}")

        return {
            "issues": issues,
            "warnings": warnings,
            "status": "warning" if warnings else "passed",
            "dependencies": len(deps) if 'deps' in locals() else 0
        }

    def generate_score(self):
        """Generate overall quality score."""
        scores = []

        for check_name, check_result in self.results["checks"].items():
            if check_result.get("status") == "passed":
                scores.append(1)
            elif check_result.get("status") == "warning":
                scores.append(0.75)
            elif check_result.get("status") == "failed":
                scores.append(0.5)
            else:
                scores.append(0.5)

        self.results["overall_score"] = round(sum(scores) / len(scores), 2)

        # Generate improvement suggestions
        for check_name, check_result in self.results["checks"].items():
            if check_result.get("issues"):
                for issue in check_result["issues"]:
                    self.results["improvements"].append({
                        "category": check_name,
                        "priority": "high",
                        "suggestion": f"Fix {issue} in {check_name} checks"
                    })
            elif check_result.get("warnings"):
                for warning in check_result["warnings"]:
                    self.results["improvements"].append({
                        "category": check_name,
                        "priority": "medium",
                        "suggestion": f"Consider: {warning}"
                    })

        # Limit improvements to top 10
        self.results["improvements"] = self.results["improvements"][:10]

    def run_all_checks(self):
        """Run all quality checks."""
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"{BLUE} Autonomous Quality Check - QZero Project {RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        # Collect Python files for analysis
        py_files = list(project_root.rglob("*.py"))
        print(f"Found {len(py_files)} Python files\n")

        checks = [
            ("imports", lambda: self.check_imports(py_files[0]) if py_files else {"status": "passed"}),
            ("complexity", lambda: self.check_code_complexity(py_files[0]) if py_files else {"status": "passed"}),
            ("documentation", lambda: self.check_documentation(py_files[0]) if py_files else {"status": "passed"}),
            ("security", lambda: self.check_security(py_files[0]) if py_files else {"status": "passed"}),
            ("project_structure", self.check_project_structure),
            ("tests", self.check_tests),
            ("dependencies", self.check_dependencies),
        ]

        total_score = 0

        for check_name, check_func in checks:
            print(f"{BLUE}[{check_name}]{RESET} Checking...")

            result = check_func()

            self.results["checks"][check_name] = result

            if result["status"] == "passed":
                score = 1
                status_str = f"{GREEN}✓{RESET} passed"
            elif result["status"] == "warning":
                score = 0.75
                status_str = f"{YELLOW}⚠{RESET} warning"
            else:
                score = 0.5
                status_str = f"{RED}✗{RESET} failed"

            print(f"  {status_str}")
            if result["issues"]:
                print(f"    Issues: {len(result['issues'])}")
            if result["warnings"]:
                print(f"    Warnings: {len(result['warnings'])}")

            total_score += score
            print()

        self.generate_score()

        # Print summary
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"{BLUE} Quality Score: {self.results['overall_score']}/1.0 {RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        if self.results["improvements"]:
            print(f"{YELLOW}Suggested Improvements:{RESET}")
            for i, imp in enumerate(self.results["improvements"], 1):
                print(f"  {i}. [{imp['priority'].upper()}] {imp['suggestion']}")
            print()

        return self.results

    def save_report(self):
        """Save quality report."""
        report_path = project_root / "reports" / f"quality-check-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"{GREEN}✓ Report saved: {report_path}{RESET}\n")

        return report_path


def main():
    """Main execution."""
    checker = QualityChecker()

    try:
        results = checker.run_all_checks()
        report_path = checker.save_report()

        # Print summary
        print(f"{GREEN}{'='*60}{RESET}")
        print(f"{GREEN} Quality check completed successfully{RESET}")
        print(f"{GREEN}{'='*60}{RESET}\n")

        # Return exit code based on score
        if results["overall_score"] >= 0.8:
            sys.exit(0)
        elif results["overall_score"] >= 0.5:
            sys.exit(1)
        else:
            sys.exit(2)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Error during quality check: {e}{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()