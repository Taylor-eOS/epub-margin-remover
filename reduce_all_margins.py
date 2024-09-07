import os
import zipfile
import re
import shutil

NEW_MARGIN = "0 !important"
NEW_PADDING = "0 !important"

def replace_margins_and_padding_in_css(css_content):
    css_content = re.sub(r'margin(-top|-bottom|-left|-right)?\s*:\s*[0-9.]+\s*[\w%]*\s*;', f'margin: {NEW_MARGIN};', css_content)
    css_content = re.sub(r'padding(-top|-bottom|-left|-right)?\s*:\s*[0-9.]+\s*[\w%]*\s*;', f'padding: {NEW_PADDING};', css_content)
    return css_content

def process_epub(epub_path, output_folder):
    epub_filename = os.path.basename(epub_path)
    output_path = os.path.join(output_folder, epub_filename)

    temp_dir = os.path.join(output_folder, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.css'):
                css_file_path = os.path.join(root, file)
                with open(css_file_path, 'r', encoding='utf-8') as css_file:
                    css_content = css_file.read()

                new_css_content = replace_margins_and_padding_in_css(css_content)

                with open(css_file_path, 'w', encoding='utf-8') as css_file:
                    css_file.write(new_css_content)

    epub_file_path = shutil.make_archive(output_path, 'zip', temp_dir)
    
    shutil.move(epub_file_path, output_path)

    shutil.rmtree(temp_dir)

    print(f"Processed EPUB: {epub_filename}")

def main():
    epub_folder = "."
    output_folder = "./processed_epubs"
    
    os.makedirs(output_folder, exist_ok=True)

    epub_files = [os.path.join(epub_folder, f) for f in os.listdir(epub_folder) if f.endswith('.epub')]
    
    if not epub_files:
        print("No EPUB files found")
        return
    
    for epub_file in epub_files:
        process_epub(epub_file, output_folder)

if __name__ == "__main__":
    main()
