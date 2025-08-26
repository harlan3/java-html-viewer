import os
import re
from pathlib import Path
import html
import sys

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
    </style>
</head>
<body>
    <pre>{content}</pre>
</body>
</html>
"""

def find_java_files(directory):
    """Find all .java files in the directory and its subdirectories."""
    java_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))
    return java_files

def get_class_and_package(file_path):
    """Extract the class name and package from a Java file."""
    package = ""
    class_name = None
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Extract package declaration
        package_match = re.search(r'^\s*package\s+([a-zA-Z0-9_.]+)\s*;', content, re.MULTILINE)
        if package_match:
            package = package_match.group(1)
        # Extract class name
        class_match = re.search(r'\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b', content)
        if class_match:
            class_name = class_match.group(1)
    return class_name, package

def create_class_map(java_files):
    """Create a map of (package, class_name) to their file paths."""
    class_map = {}
    for file_path in java_files:
        class_name, package = get_class_and_package(file_path)
        if class_name:
            class_map[(package, class_name)] = file_path
    return class_map

def escape_html(text):
    """Escape HTML special characters."""
    return html.escape(text)

def process_single_line_comments(line):
    """Wrap single-line comments in a span with comment class."""
    return re.sub(r'(//[^\n]*)', r'<span class="comment">\1</span>', line)

def create_links(content, class_map, input_dir, output_dir, current_file):
    """Add hyperlinks to class references with correct relative paths, considering packages."""
    current_package = get_class_and_package(current_file)[1]

    def replace_class(match):
        class_name = match.group(0)
        # Try to resolve the class in the current package first
        key = (current_package, class_name)
        if key not in class_map:
            # If not found in current package, check other packages
            for (pkg, cls), file_path in class_map.items():
                if cls == class_name:
                    key = (pkg, cls)
                    break
            else:
                return class_name  # No match found, return original text

        # Get the target HTML file path
        target_file = class_map[key].replace(input_dir, output_dir).replace('.java', '.html')
        # Calculate relative path from the current HTML file to the target HTML file
        current_dir = os.path.dirname(current_file.replace(input_dir, output_dir).replace('.java', '.html'))
        relative_path = os.path.relpath(target_file, current_dir).replace('\\', '/')
        return f'<a href="{relative_path}">{class_name}</a>'

    # Link class names (word boundaries to avoid partial matches)
    content = re.sub(r'\b[A-Z][A-Za-z0-9_]*\b', replace_class, content)
    return content

def convert_file(file_path, class_map, input_dir, output_dir):
    """Convert a single Java file to HTML with line numbers."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    content_lines = []
    in_block_comment = False
    line_number = 1

    for line in lines:
        line_content = line.rstrip('\n')
        remaining_content = line_content

        while remaining_content:
            if in_block_comment:
                # Look for end of block comment
                end_match = re.search(r'(.*?)\*/', remaining_content)
                if end_match:
                    # Found end of block comment
                    comment_part = end_match.group(1) + '*/'
                    escaped_comment = escape_html(comment_part)
                    comment_content = process_single_line_comments(escaped_comment)
                    comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                    content_lines.append(
                        f'<div class="line-container"><span class="line-number">{line_number}</span>'
                        f'<span class="code-line"><span class="comment">{comment_content}</span></span></div>'
                    )
                    in_block_comment = False
                    # Process remaining content after */
                    remaining_content = remaining_content[end_match.end():]
                    if remaining_content:
                        escaped_line = escape_html(remaining_content)
                        line_content_processed = process_single_line_comments(escaped_line)
                        line_content_processed = create_links(line_content_processed, class_map, input_dir, output_dir, file_path)
                        content_lines.append(
                            f'<div class="line-container"><span class="line-number">{line_number}</span>'
                            f'<span class="code-line">{line_content_processed}</span></div>'
                        )
                    line_number += 1
                else:
                    # Entire line is part of block comment
                    escaped_line = escape_html(remaining_content)
                    comment_content = process_single_line_comments(escaped_line)
                    comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                    content_lines.append(
                        f'<div class="line-container"><span class="line-number">{line_number}</span>'
                        f'<span class="code-line"><span class="comment">{comment_content}</span></span></div>'
                    )
                    line_number += 1
                    remaining_content = ""
            else:
                # Look for start of block comment
                start_match = re.search(r'(/\*\*?)', remaining_content)
                if start_match:
                    # Process content before /*
                    pre_comment = remaining_content[:start_match.start()]
                    if pre_comment:
                        escaped_pre_comment = escape_html(pre_comment)
                        pre_comment_content = process_single_line_comments(escaped_pre_comment)
                        pre_comment_content = create_links(pre_comment_content, class_map, input_dir, output_dir, file_path)
                        content_lines.append(
                            f'<div class="line-container"><span class="line-number">{line_number}</span>'
                            f'<span class="code-line">{pre_comment_content}</span></div>'
                        )
                        line_number += 1
                    # Start block comment
                    in_block_comment = True
                    remaining_content = remaining_content[start_match.start():]
                    # Check if */ is on the same line
                    end_match = re.search(r'(.*?)\*/', remaining_content)
                    if end_match:
                        comment_part = end_match.group(1) + '*/'
                        escaped_comment = escape_html(comment_part)
                        comment_content = process_single_line_comments(escaped_comment)
                        comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                        content_lines.append(
                            f'<div class="line-container"><span class="line-number">{line_number}</span>'
                            f'<span class="code-line"><span class="comment">{comment_content}</span></span></div>'
                        )
                        in_block_comment = False
                        remaining_content = remaining_content[end_match.end():]
                        if remaining_content:
                            escaped_line = escape_html(remaining_content)
                            line_content_processed = process_single_line_comments(escaped_line)
                            line_content_processed = create_links(line_content_processed, class_map, input_dir, output_dir, file_path)
                            content_lines.append(
                                f'<div class="line-container"><span class="line-number">{line_number}</span>'
                                f'<span class="code-line">{line_content_processed}</span></div>'
                            )
                        line_number += 1
                    else:
                        # Block comment continues to next line
                        escaped_line = escape_html(remaining_content)
                        comment_content = process_single_line_comments(escaped_line)
                        comment_content = create_links(comment_content, class_map, input_dir, output_dir, file_path)
                        content_lines.append(
                            f'<div class="line-container"><span class="line-number">{line_number}</span>'
                            f'<span class="code-line"><span class="comment">{comment_content}</span></span></div>'
                        )
                        line_number += 1
                        remaining_content = ""
                else:
                    # No block comment, process as normal line
                    escaped_line = escape_html(remaining_content)
                    line_content_processed = process_single_line_comments(escaped_line)
                    line_content_processed = create_links(line_content_processed, class_map, input_dir, output_dir, file_path)
                    content_lines.append(
                        f'<div class="line-container"><span class="line-number">{line_number}</span>'
                        f'<span class="code-line">{line_content_processed}</span></div>'
                    )
                    line_number += 1
                    remaining_content = ""

    # Join lines with newlines
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

def main():
    
    if len(sys.argv) < 2:
        print("Usage: generate_html_src <java_source_tree>")
        return
    INPUT_DIR = sys.argv[1]
    
    """Main function to process all Java files."""
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Find all Java files
    java_files = find_java_files(INPUT_DIR)
    if not java_files:
        print(f"No Java files found in {INPUT_DIR}")
        return

    # Create class map
    class_map = create_class_map(java_files)

    # Convert each Java file to HTML
    for file_path in java_files:
        convert_file(file_path, class_map, INPUT_DIR, OUTPUT_DIR)
        print(f"Converted {file_path} to HTML")

if __name__ == "__main__":
    main()