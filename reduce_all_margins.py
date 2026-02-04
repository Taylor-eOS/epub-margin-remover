import os
import shutil
from calibre.ebooks.oeb.polish.container import get_container

epub_folder = "./input_files"
output_folder = "./processed_epubs"

def process_epub(input_path, output_path):
    shutil.copy(input_path, output_path)
    try:
        container = get_container(output_path)
        modified = False
        for name in container.manifest_items_of_type("text/css"):
            css_text = container.raw_data(name, decode=True)
            new_rule = "\nbody {\n    margin: 0;\n    padding: 0;\n}\n"
            if new_rule not in css_text:
                new_css_text = css_text + new_rule
                container.replace(name, new_css_text)
                modified = True
        if modified:
            print(f"Processed and saved: {output_path}")
        else:
            print(f"No changes needed in CSS for: {output_path}")
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
