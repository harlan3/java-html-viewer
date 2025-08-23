REM remove src_html directory
rd /s /q "src_html"

REM Generate html from Java source code. Must pass the absolute java_source_tree path.
python3 scripts\generate_html_src.py %1

REM remove Content.mm
del Content.mm

REM Generate mindmap
python3 scripts\generate_mindmap.py %1