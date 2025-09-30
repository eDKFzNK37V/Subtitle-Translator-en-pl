#!/usr/bin/env python3
"""
Complete Function Analysis Tool
Analyzes all Python files in the main directory to find:
1. All function definitions and their locations
2. All function calls and where they originate
3. Unused functions (defined but never called)

This script follows the copilot-instructions.md patterns for comprehensive analysis.
"""

import ast
import os
import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FunctionInfo:
    """Information about a function definition."""
    name: str
    file_path: str
    line_number: int
    class_name: Optional[str] = None
    is_method: bool = False
    args: Optional[List[str]] = None
    docstring: Optional[str] = None

@dataclass
class FunctionCall:
    """Information about a function call."""
    function_name: str
    file_path: str
    line_number: int
    context: str  # The line of code where the call occurs

class FunctionAnalyzer:
    """Analyzes Python files to extract function definitions and calls."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.functions: Dict[str, List[FunctionInfo]] = {}
        self.function_calls: Dict[str, List[FunctionCall]] = {}
        self.imports: Dict[str, Set[str]] = {}  # file -> set of imported modules/functions
        
    def analyze_directory(self) -> None:
        """Analyze all Python files in the directory."""
        python_files = list(self.root_dir.glob("*.py"))
        
        print(f"Found {len(python_files)} Python files to analyze...")
        
        for py_file in python_files:
            print(f"Analyzing {py_file.name}...")
            try:
                self._analyze_file(py_file)
            except Exception as e:
                print(f"Error analyzing {py_file.name}: {e}")
                continue
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            print(f"Syntax error in {file_path.name}: {e}")
            return
        
        # Extract function definitions
        self._extract_functions(tree, str(file_path))
        
        # Extract function calls
        self._extract_function_calls(tree, str(file_path), content.splitlines())
        
        # Extract imports
        self._extract_imports(tree, str(file_path))
    
    def _extract_functions(self, tree: ast.AST, file_path: str) -> None:
        """Extract all function definitions from the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Determine if it's a method (inside a class)
                class_name = None
                is_method = False
                
                # Walk up the tree to find if this function is inside a class
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        # Check if the function is a direct child of this class
                        if node in parent.body:
                            class_name = parent.name
                            is_method = True
                            break
                
                # Extract arguments
                args = []
                if node.args.args:
                    args = [arg.arg for arg in node.args.args]
                
                # Extract docstring
                docstring = None
                if (node.body and isinstance(node.body[0], ast.Expr) and 
                    isinstance(node.body[0].value, ast.Constant) and 
                    isinstance(node.body[0].value.value, str)):
                    docstring = node.body[0].value.value.strip()
                
                func_info = FunctionInfo(
                    name=node.name,
                    file_path=file_path,
                    line_number=node.lineno,
                    class_name=class_name,
                    is_method=is_method,
                    args=args,
                    docstring=docstring
                )
                
                if node.name not in self.functions:
                    self.functions[node.name] = []
                self.functions[node.name].append(func_info)
    
    def _extract_function_calls(self, tree: ast.AST, file_path: str, lines: List[str]) -> None:
        """Extract all function calls from the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_function_name_from_call(node)
                if func_name:
                    # Get the context (the actual line of code)
                    context = ""
                    if hasattr(node, 'lineno') and node.lineno <= len(lines):
                        context = lines[node.lineno - 1].strip()
                    
                    call_info = FunctionCall(
                        function_name=func_name,
                        file_path=file_path,
                        line_number=getattr(node, 'lineno', 0),
                        context=context
                    )
                    
                    if func_name not in self.function_calls:
                        self.function_calls[func_name] = []
                    self.function_calls[func_name].append(call_info)
    
    def _get_function_name_from_call(self, call_node: ast.Call) -> Optional[str]:
        """Extract function name from a call node."""
        if isinstance(call_node.func, ast.Name):
            # Simple function call: func()
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            # Method call: obj.method() or module.func()
            return call_node.func.attr
        elif isinstance(call_node.func, ast.Subscript):
            # Callable subscript: func[key]()
            return None
        else:
            return None
    
    def _extract_imports(self, tree: ast.AST, file_path: str) -> None:
        """Extract import statements from the AST."""
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                for alias in node.names:
                    imports.add(alias.name)
        
        self.imports[file_path] = imports
    
    def find_unused_functions(self) -> Dict[str, List[FunctionInfo]]:
        """Find functions that are defined but never called."""
        unused = {}
        
        for func_name, definitions in self.functions.items():
            # Skip special methods and common entry points
            if (func_name.startswith('__') or 
                func_name in ['main', 'run_gui', 'run_gui_nllb'] or
                func_name.startswith('_')):  # Private functions might be used internally
                continue
            
            # Check if this function is called anywhere
            if func_name not in self.function_calls:
                unused[func_name] = definitions
        
        return unused
    
    def generate_report(self) -> str:
        """Generate a comprehensive report of all functions."""
        report = []
        
        report.append("=" * 80)
        report.append("COMPLETE FUNCTION ANALYSIS REPORT")
        report.append("Generated for troubleshooting purposes")
        report.append("=" * 80)
        
        # Summary statistics
        total_functions = sum(len(defs) for defs in self.functions.values())
        total_calls = sum(len(calls) for calls in self.function_calls.values())
        unique_functions = len(self.functions)
        unique_called_functions = len(self.function_calls)
        
        report.append(f"\nSUMMARY STATISTICS:")
        report.append(f"Total function definitions: {total_functions}")
        report.append(f"Unique function names: {unique_functions}")
        report.append(f"Total function calls: {total_calls}")
        report.append(f"Unique called function names: {unique_called_functions}")
        
        # Group functions by file
        functions_by_file = {}
        for func_name, definitions in self.functions.items():
            for func_def in definitions:
                file_name = os.path.basename(func_def.file_path)
                if file_name not in functions_by_file:
                    functions_by_file[file_name] = []
                functions_by_file[file_name].append((func_name, func_def))
        
        # Generate detailed function list by file
        report.append(f"\n" + "=" * 80)
        report.append("ALL FUNCTIONS BY FILE")
        report.append("=" * 80)
        
        for file_name in sorted(functions_by_file.keys()):
            report.append(f"\nFILE: {file_name}")
            report.append("-" * 50)
            
            # Sort functions by line number
            file_functions = sorted(functions_by_file[file_name], key=lambda x: x[1].line_number)
            
            for func_name, func_def in file_functions:
                class_info = f" (in class {func_def.class_name})" if func_def.class_name else ""
                args_info = f"({', '.join(func_def.args)})" if func_def.args else "()"
                
                report.append(f"  • {func_name}{args_info} [Line {func_def.line_number}]{class_info}")
                
                if func_def.docstring:
                    # Truncate long docstrings
                    doc_preview = func_def.docstring[:100] + "..." if len(func_def.docstring) > 100 else func_def.docstring
                    report.append(f"    Doc: {doc_preview}")
                
                # Show where this function is called
                if func_name in self.function_calls:
                    calls = self.function_calls[func_name]
                    report.append(f"    Called in {len(calls)} place(s):")
                    for call in calls[:10]:  # Limit to first 10 calls
                        call_file = os.path.basename(call.file_path)
                        report.append(f"      - {call_file}:{call.line_number} → {call.context[:80]}")
                    if len(calls) > 10:
                        report.append(f"      ... and {len(calls) - 10} more calls")
                else:
                    report.append(f"    ⚠️  NOT CALLED ANYWHERE (potential unused function)")
        
        # Find and report unused functions
        unused_functions = self.find_unused_functions()
        if unused_functions:
            report.append(f"\n" + "=" * 80)
            report.append("POTENTIALLY UNUSED FUNCTIONS")
            report.append("=" * 80)
            report.append("These functions are defined but never called (excluding private and special methods):")
            
            for func_name, definitions in unused_functions.items():
                for func_def in definitions:
                    file_name = os.path.basename(func_def.file_path)
                    report.append(f"  • {func_name} in {file_name}:{func_def.line_number}")
        
        # Show functions called but not defined (external or missing)
        undefined_calls = {}
        for func_name, calls in self.function_calls.items():
            if func_name not in self.functions:
                undefined_calls[func_name] = calls
        
        if undefined_calls:
            report.append(f"\n" + "=" * 80)
            report.append("FUNCTIONS CALLED BUT NOT DEFINED LOCALLY")
            report.append("=" * 80)
            report.append("These are likely imported functions, built-ins, or external library calls:")
            
            for func_name in sorted(undefined_calls.keys()):
                calls = undefined_calls[func_name]
                report.append(f"  • {func_name} (called {len(calls)} time(s))")
                # Show first few call locations
                for call in calls[:3]:
                    call_file = os.path.basename(call.file_path)
                    report.append(f"    - {call_file}:{call.line_number}")
                if len(calls) > 3:
                    report.append(f"    ... and {len(calls) - 3} more")
        
        return "\n".join(report)
    
    def save_report(self, output_file: str) -> None:
        """Save the report to a file."""
        report = self.generate_report()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {output_file}")

def main():
    """Main function to run the analysis."""
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Starting comprehensive function analysis...")
    print(f"Analyzing directory: {script_dir}")
    
    analyzer = FunctionAnalyzer(script_dir)
    analyzer.analyze_directory()
    
    # Generate and save report
    output_file = os.path.join(script_dir, "function_analysis_report.txt")
    analyzer.save_report(output_file)
    
    print(f"\nAnalysis complete!")
    print(f"Found {len(analyzer.functions)} unique function names")
    print(f"Total function definitions: {sum(len(defs) for defs in analyzer.functions.values())}")
    print(f"Total function calls: {sum(len(calls) for calls in analyzer.function_calls.values())}")

if __name__ == "__main__":
    main()