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
        pre {{ white-space: pre-wrap; }}
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

def process_comments(content):
    """Wrap comments in a span with comment class."""
    # Handle block comments
    content = re.sub(r'(/\*.*?\*/)', r'<span class="comment">\1</span>', content, flags=re.DOTALL)
    # Handle single-line comments
    content = re.sub(r'(//[^\n]*)', r'<span class="comment">\1</span>', content)
    return content

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
    """Convert a single Java file to HTML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Escape HTML characters
    content = escape_html(content)
    # Process comments
    content = process_comments(content)
    # Add links to class references
    content = create_links(content, class_map, input_dir, output_dir, file_path)

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