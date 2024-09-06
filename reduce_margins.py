import os
import zipfile
import re
import shutil

# Define the new fixed margin and padding value you want to apply
NEW_MARGIN = "0 !important"  # Use !important to try overriding reader defaults
NEW_PADDING = "0 !important"

def replace_margins_and_padding_in_css(css_content):
    """Replaces all margin and padding rules in the CSS content with 0."""
    # Replace any instance of margin, margin-top, margin-bottom, padding, etc.
    # Matches both shorthand and individual margin/padding properties
    css_content = re.sub(r'margin(-top|-bottom|-left|-right)?\s*:\s*[0-9.]+(em|px|rem|%)?', f'margin: {NEW_MARGIN};', css_content)
    css_content = re.sub(r'padding(-top|-bottom|-left|-right)?\s*:\s*[0-9.]+(em|px|rem|%)?', f'padding: {NEW_PADDING};', css_content)
    return css_content

def process_epub(epub_path, output_folder):
    """Unzip the EPUB, replace margins and padding in CSS, and repackage the EPUB."""
    epub_filename = os.path.basename(epub_path)
    output_path = os.path.join(output_folder, epub_filename)

    # Create a temporary working directory
    temp_dir = os.path.join(output_folder, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Unzip EPUB to the temporary directory
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Process all CSS files in the extracted EPUB
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.css'):
                css_file_path = os.path.join(root, file)
                with open(css_file_path, 'r', encoding='utf-8') as css_file:
                    css_content = css_file.read()

                # Replace margins and padding in the CSS content
                new_css_content = replace_margins_and_padding_in_css(css_content)

                # Write the modified CSS back to the file
                with open(css_file_path, 'w', encoding='utf-8') as css_file:
                    css_file.write(new_css_content)

    # Repackage the EPUB (re-zip it)
    epub_file_path = shutil.make_archive(output_path, 'zip', temp_dir)
    
    # Rename the .zip file back to .epub
    shutil.move(epub_file_path, output_path)

    # Clean up the temporary directory
    shutil.rmtree(temp_dir)

    print(f"Processed EPUB: {epub_filename}")

def main():
    # Define the folder where your EPUBs are located
    epub_folder = "."  # Adjust this path as needed
    output_folder = "./processed_epubs"  # Folder for processed EPUBs
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Find all EPUB files in the epub_folder directory
    epub_files = [os.path.join(epub_folder, f) for f in os.listdir(epub_folder) if f.endswith('.epub')]
    
    if not epub_files:
        print("No EPUB files found in the specified directory.")
        return
    
    # Process each EPUB file
    for epub_file in epub_files:
        process_epub(epub_file, output_folder)

if __name__ == "__main__":
    main()
