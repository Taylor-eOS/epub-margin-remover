import os
import re
import shutil
from calibre.ebooks.oeb.polish.container import get_container

epub_folder = "./input_files"
output_folder = "./processed_epubs"

def replace_margins(css_content):
    lines = css_content.splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if ':' in stripped and stripped.endswith(';'):
            prop, value = stripped.split(':', 1)
            lname = prop.strip().lower()
            if lname.startswith('margin') or lname.startswith('padding'):
                line = f"{prop.strip()}: 0 !important;"
        new_lines.append(line)
    return "\n".join(new_lines)

def replace_style_block(match):
    open_tag = match.group(1)
    inner = match.group(2)
    new_inner = replace_margins(inner)
    return f"{open_tag}{new_inner}</style>"

def replace_style_attr_double(match):
    inner = match.group(1)
    new_inner = replace_margins(inner)
    return f'style="{new_inner}"'

def replace_style_attr_single(match):
    inner = match.group(1)
    new_inner = replace_margins(inner)
    return f"style='{new_inner}'"

def process_epub(input_path, output_path):
    shutil.copy(input_path, output_path)
    try:
        container = get_container(output_path)
        modified = False
        for name, mt in list(container.mime_map.items()):
            if mt == "application/vnd.adobe-page-template+xml":
                container.remove_item(name)
                modified = True
            elif mt == "text/css":
                css_text = container.raw_data(name, decode=True)
                new_css_text = replace_margins(css_text)
                if new_css_text != css_text:
                    container.replace(name, new_css_text)
                    modified = True
            elif mt in ("application/xhtml+xml", "text/html"):
                txt = container.raw_data(name, decode=True)
                new_txt = re.sub(r'(<style\b[^>]*>)(.*?)</style>', replace_style_block, txt, flags=re.IGNORECASE | re.DOTALL)
                new_txt = re.sub(r'style\s*=\s*"([^"]*?)"', replace_style_attr_double, new_txt, flags=re.IGNORECASE | re.DOTALL)
                new_txt = re.sub(r"style\s*=\s*'([^']*?)'", replace_style_attr_single, new_txt, flags=re.IGNORECASE | re.DOTALL)
                if new_txt != txt:
                    container.replace(name, new_txt)
                    modified = True
        if modified:
            container.commit()
            print(f"Processed and saved: {output_path}")
        else:
            print(f"No CSS changes needed in: {output_path}")
            os.remove(output_path)
    except Exception as e:
        print(f"Failed to process {output_path}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)

def main():
    os.makedirs(output_folder, exist_ok=True)
    try:
        epub_files = [os.path.join(epub_folder, f) for f in os.listdir(epub_folder) if f.lower().endswith(".epub")]
    except FileNotFoundError:
        print(f"The folder '{epub_folder}' does not exist.")
        return
    if not epub_files:
        print(f"No EPUB files found in '{epub_folder}'.")
        return
    for epub_file in epub_files:
        epub_filename = os.path.basename(epub_file)
        output_path = os.path.join(output_folder, epub_filename)
        process_epub(epub_file, output_path)

if __name__ == "__main__":
    main()

