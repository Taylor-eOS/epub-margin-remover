import os
import re
import tempfile
from ebooklib import epub, ITEM_STYLE

epub_folder = "./input_files"  # Ensure this points to your input_files subfolder
output_folder = "./processed_epubs"

def replace_margins(css_content):
    css_content = re.sub(
        r'margin(?:-top|-bottom|-left|-right)?\s*:\s*[0-9.]+\s*(?:px|em|rem|%)?\s*;',
        'margin: 0 !important;',
        css_content,
        flags=re.IGNORECASE)
    css_content = re.sub(
        r'padding(?:-top|-bottom|-left|-right)?\s*:\s*[0-9.]+\s*(?:px|em|rem|%)?\s*;',
        'padding: 0 !important;',
        css_content,
        flags=re.IGNORECASE)
    return css_content

def main():
    os.makedirs(output_folder, exist_ok=True)
    try:
        epub_files = [
            os.path.join(epub_folder, f)
            for f in os.listdir(epub_folder)
            if f.lower().endswith('.epub')]
    except FileNotFoundError:
        print(f"The folder '{epub_folder}' does not exist.")
        return
    if not epub_files:
        print(f"No EPUB files found in the {epub_folder} directory.")
        return
    for epub_file in epub_files:
        epub_filename = os.path.basename(epub_file)
        output_path = os.path.join(output_folder, epub_filename)
        try:
            book = epub.read_epub(epub_file)
            for item in book.get_items_of_type(ITEM_STYLE):
                css_content = item.get_content().decode('utf-8')
                new_css_content = replace_margins(css_content)
                item.set_content(new_css_content.encode('utf-8'))
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                temp_path = tmp_file.name
            epub.write_epub(temp_path, book)
            os.replace(temp_path, output_path)
            print(f"Processed EPUB saved to: {output_path}")
        except Exception as e:
            print(f"Failed to process {os.path.splitext(epub_filename)[0]}: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    main()
