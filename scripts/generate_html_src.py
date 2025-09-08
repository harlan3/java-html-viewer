import os
import re
from pathlib import Path
import html
import sys
import shutil

# Configuration
#INPUT_DIR = "C:\\Users\harla\\java2html\\src"  # Directory containing Java source files

OUTPUT_DIR = "src_html"  # Directory for HTML output
BACKGROUND_COLOR = "white"
COMMENT_COLOR = "green"
LINK_COLOR = "blue"

# CSS styles for HTML output
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ background-color: {bg_color}; font-family: monospace; }}
        .comment {{ color: {comment_color}; }}
        a {{ color: {link_color}; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        pre {{ white-space: pre-wrap; margin: 0; }}
        .line-container {{ 
            display: flex; 
            align-items: flex-start; 
            line-height: 1.0; 
            margin-bottom: -0.8em;
        }}
        .line-number {{ 
            display: inline-block; 
            width: 40px; 
            text-align: right; 
            padding-right: 10px; 
            color: gray; 
            user-select: none; 
        }}
        .code-line {{ display: inline; }}
        .empty-line {{ height: 1em; }}
    </style>
</head>
<body>
    <pre>{content}</pre>
</body>
</html>
"""

def find_files(directory):
    """Find all .java, .xml, .json, and .dat files in the directory and its subdirectories."""
    java_files = []
    pass_through_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
            elif file.endswith((".xml", ".json", ".dat")):
                pass_through_files.append(os.path.join(root, file))
    return java_files, pass_through_files

def get_primary_type_and_package(file_path):
    """Extract the primary type name (class, interface, enum) and package from a Java file."""
    package = ""
    primary_type = None
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Extract package declaration
        package_match = re.search(r'^\s*package\s+([a-zA-Z0-9_.]+)\s*;', content, re.MULTILINE)
        if package_match:
            package = package_match.group(1)
        # Extract primary type name (look for public first, then any)
        type_match = re.search(r'\bpublic\s+(?:class|interface|enum|record|@interface)\s+([A-Za-z_][A-Za-z0-9_]*)\b', content)
        if not type_match:
            type_match = re.search(r'\b(?:class|interface|enum|record|@interface)\s+([A-Za-z_][A-Za-z0-9_]*)\b', content)
        if type_match:
            primary_type = type_match.group(1)
    return primary_type, package

def extract_all_types(content):
    """Extract all type names (classes, interfaces, enums, records, annotations) from the content."""
    return re.findall(r'\b(?:class|interface|enum|record|@interface)\s+([A-Za-z_][A-Za-z0-9_]*)\b', content)

def create_class_map(java_files):
    """Create a map of (package, type_name) to their file paths for all types."""
    class_map = {}
    for file_path in java_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        package_match = re.search(r'^\s*package\s+([a-zA-Z0-9_.]+)\s*;', content, re.MULTILINE)
        package = package_match.group(1) if package_match else ""
        type_names = extract_all_types(content)
        for type_name in type_names:
            class_map[(package, type_name)] = file_path
    return class_map

def extract_methods(file_path):
    """Extract method names and their starting line numbers from a Java file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    methods = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            continue
        match = re.match(r'\s*(?:(?:public|protected|private|static|final|native|synchronized|abstract|transient|volatile)\s+)*([\w<>\[\]]+)\s+(\w+)\s*\([^\)]*\)\s*(?:throws\s+[\w\.,\s]+)?\s*[{;]?', line)
        if match and match.group(2) != 'if':  # Exclude 'if' statements
            method_name = match.group(2)
            methods.append((method_name, i + 1))
    return methods

def escape_html(text):
    """Escape HTML special characters."""
    return html.escape(text)

def process_single_line_comments(line):
    """Wrap single-line comments in a span with comment class."""
    return re.sub(r'(//[^\n]*)', r'<span class="comment">\1</span>', line)

def create_links(content, class_map, input_dir, output_dir, current_file):
    """Add hyperlinks to type references (classes, interfaces, enums, exceptions) with correct relative paths, considering packages."""
    current_package = get_primary_type_and_package(current_file)[1]

    def replace_class(match):
        type_name = match.group(0)
        # Try to resolve the type in the current package first
        key = (current_package, type_name)
        if key not in class_map:
            # If not found in current package, check other packages
            for (pkg, cls), file_path in class_map.items():
                if cls == type_name:
                    key = (pkg, cls)
                    break
            else:
                return type_name  # No match found, return original text

        # Get the target HTML file path
        target_file = class_map[key].replace(input_dir, output_dir).replace('.java', '.html')
        # Calculate relative path from the current HTML file to the target HTML file
        current_dir = os.path.dirname(current_file.replace(input_dir, output_dir).replace('.java', '.html'))
        relative_path = os.path.relpath(target_file, current_dir).replace('\\', '/')
        return f'<a href="{relative_path}">{type_name}</a>'

    # Link type names (word boundaries to avoid partial matches)
    content = re.sub(r'\b[A-Z][A-Za-z0-9_]*\b', replace_class, content)
    return content

def create_method_links(content, method_map, class_map, input_dir, output_dir, current_file, current_package, current_type):
    """Add hyperlinks to method references if possible, excluding 'if' statements."""
    def replace_method(match):
        method_name = match.group(1)
        if method_name == 'if':  # Skip 'if' statements
            return method_name
        # First, check if in current class
        key = (current_package, current_type, method_name)
        if key in method_map:
            line_num = method_map[key]
            return f'<a href="#L{line_num}">{method_name}</a>'
        # Else, find all possible
        possible = []
        for (pkg, cls, meth), ln in method_map.items():
            if meth == method_name:
                possible.append((pkg, cls, ln))
        if len(possible) == 1:
            pkg, cls, ln = possible[0]
            target_key = (pkg, cls)
            if target_key in class_map:
                target_file = class_map[target_key].replace(input_dir, output_dir).replace('.java', '.html')
                current_html = current_file.replace(input_dir, output_dir).replace('.java', '.html')
                current_dir = os.path.dirname(current_html)
                relative_path = os.path.relpath(target_file, current_dir).replace('\\', '/')
                return f'<a href="{relative_path}#L{ln}">{method_name}</a>'
        # Else, no link
        return method_name

    # Link method names only if followed by '(' (for calls and definitions)
    content = re.sub(r'\b([a-z][A-Za-z0-9_]*)(?=\s*\()', replace_method, content)
    return content

def convert_file(file_path, class_map, method_map, input_dir, output_dir):
    """Convert a single Java file to HTML with line numbers, comments, links, method anchors, and preserved empty lines."""
    current_type, current_package = get_primary_type_and_package(file_path)
    # Get method start lines for this class
    method_starts = set()
    for (pkg, cls, meth), ln in method_map.items():
        if pkg == current_package and cls == current_type:
            method_starts.add(ln)

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    content_lines = []
    in_block_comment = False
    line_number = 1

    for line in lines:
        line_content = line.rstrip('\n')
        # Check for empty line (only whitespace)
        if not line_content.strip():
            content_lines.append(f'<div class="line-container"><span class="line-number">{line_number}</span><span class="code-line empty-line"></span></div>')
            line_number += 1
            continue

        remaining_content = line_content
        parts = []

        while remaining_content:
            if in_block_comment:
                # Look for end of block comment
                end_match = re.search(r'(.*?)\*/', remaining_content)
                if end_match:
                    comment_part = end_match.group(1) + '*/'
                    escaped_comment = escape_html(comment_part)
                    comment_content = process_single_line_comments(escaped_comment)
                    comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                    comment_content = create_method_links(comment_content, method_map, class_map, input_dir, output_dir, file_path, current_package, current_type)
                    parts.append(f'<span class="comment">{comment_content}</span>')
                    in_block_comment = False
                    remaining_content = remaining_content[end_match.end():]
                else:
                    # Entire remaining is part of block comment
                    escaped_line = escape_html(remaining_content)
                    comment_content = process_single_line_comments(escaped_line)
                    comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                    comment_content = create_method_links(comment_content, method_map, class_map, input_dir, output_dir, file_path, current_package, current_type)
                    parts.append(f'<span class="comment">{comment_content}</span>')
                    remaining_content = ""
            else:
                # Look for start of block comment
                start_match = re.search(r'(/\*\*?)', remaining_content)
                if start_match:
                    # Process content before /*
                    pre_comment = remaining_content[:start_match.start()]
                    if pre_comment:
                        escaped_pre = escape_html(pre_comment)
                        pre_processed = process_single_line_comments(escaped_pre)
                        pre_processed = create_links(pre_processed, class_map, input_dir, output_dir, file_path)
                        pre_processed = create_method_links(pre_processed, method_map, class_map, input_dir, output_dir, file_path, current_package, current_type)
                        parts.append(pre_processed)
                    # Start block comment
                    remaining_content = remaining_content[start_match.start():]
                    in_block_comment = True
                    # Check if */ on same line
                    end_match = re.search(r'(.*?)\*/', remaining_content)
                    if end_match:
                        comment_part = end_match.group(1) + '*/'
                        escaped_comment = escape_html(comment_part)
                        comment_content = process_single_line_comments(escaped_comment)
                        comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                        comment_content = create_method_links(comment_content, method_map, class_map, input_dir, output_dir, file_path, current_package, current_type)
                        parts.append(f'<span class="comment">{comment_content}</span>')
                        in_block_comment = False
                        remaining_content = remaining_content[end_match.end():]
                    else:
                        # Block continues
                        escaped_line = escape_html(remaining_content)
                        comment_content = process_single_line_comments(escaped_line)
                        comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                        comment_content = create_method_links(comment_content, method_map, class_map, input_dir, output_dir, file_path, current_package, current_type)
                        parts.append(f'<span class="comment">{comment_content}</span>')
                        remaining_content = ""
                else:
                    # No block comment, process whole remaining
                    escaped_line = escape_html(remaining_content)
                    line_processed = process_single_line_comments(escaped_line)
                    line_processed = create_links(line_processed, class_map, input_dir, output_dir, file_path)
                    line_processed = create_method_links(line_processed, method_map, class_map, input_dir, output_dir, file_path, current_package, current_type)
                    parts.append(line_processed)
                    remaining_content = ""

        # Build the line
        if parts:
            code_line = ''.join(parts)
            anchor = f'<a name="L{line_number}"></a>' if line_number in method_starts else ''
            content_lines.append(
                f'<div class="line-container"><span class="line-number">{line_number}</span><span class="code-line">{anchor}{code_line}</span></div>'
            )
        line_number += 1

    # Join lines
    content = '\n'.join(content_lines)

    # Create HTML file
    output_file = file_path.replace(input_dir, output_dir).replace('.java', '.html')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    title = os.path.basename(file_path)
    html_content = HTML_TEMPLATE.format(
        title=title,
        bg_color=BACKGROUND_COLOR,
        comment_color=COMMENT_COLOR,
        link_color=LINK_COLOR,
        content=content
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def copy_pass_through_files(pass_through_files, input_dir, output_dir):
    """Copy .xml, .json, and .dat files to the output directory without modification."""
    for file_path in pass_through_files:
        output_file = file_path.replace(input_dir, output_dir)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        shutil.copy2(file_path, output_file)
        print(f"Copied {file_path} to {output_file}")

def main():
    
    if len(sys.argv) < 2:
        print("Usage: generate_html_src <java_source_tree>")
        return
    INPUT_DIR = sys.argv[1]
    
    """Main function to process all Java files and copy pass-through files."""
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Find all Java and pass-through files
    java_files, pass_through_files = find_files(INPUT_DIR)
    if not java_files and not pass_through_files:
        print(f"No Java, XML, JSON, or DAT files found in {INPUT_DIR}")
        return

    # First pass: Create class map and method map
    class_map = create_class_map(java_files)
    method_map = {}
    for file_path in java_files:
        primary_type, package = get_primary_type_and_package(file_path)
        if primary_type:
            methods = extract_methods(file_path)
            for meth, ln in methods:
                key = (package, primary_type, meth)
                if key not in method_map:  # Take first occurrence if overloads
                    method_map[key] = ln

    # Second pass: Convert each Java file to HTML
    for file_path in java_files:
        convert_file(file_path, class_map, method_map, INPUT_DIR, OUTPUT_DIR)
        print(f"Converted {file_path} to HTML")

    # Copy pass-through files (.xml, .json, .dat)
    copy_pass_through_files(pass_through_files, INPUT_DIR, OUTPUT_DIR)

if __name__ == "__main__":
    main()