#!/bin/bash

# Remove src_html directory
rm -rf src_html

# Generate html from Java source code. Must pass the absolute java_source_tree path.
python3 scripts/generate_html_src.py $1

# Remove Content.mm
rm Content.mm

# Generate mindmap
python3 scripts/generate_mindmap.py $1