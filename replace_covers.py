import os
import sys
from calibre.ebooks.oeb.polish.container import get_container
from lxml import etree
import shutil

epub_folder = input('Folder with EPUB files: ').rstrip("/")
covers_folder = epub_folder + '_covers'
output_folder = epub_folder + '_new_covers'

def find_cover_image_name(container):
    opf = container.opf
    ns = {'opf': 'http://www.idpf.org/2007/opf'}
    manifest = opf.find('opf:manifest', ns)
    if manifest is not None:
        for item in manifest.findall('opf:item', ns):
            props = (item.get('properties') or '').split()
            if 'cover-image' in props:
                href = item.get('href')
                if href:
                    return container.href_to_name(href, container.opf_name)
        meta_cover = opf.find('.//opf:meta[@name="cover"]', ns)
        if meta_cover is not None:
            cover_id = meta_cover.get('content')
            if cover_id:
                for item in manifest.findall('opf:item', ns):
                    if item.get('id') == cover_id:
                        href = item.get('href')
                        if href:
                            return container.href_to_name(href, container.opf_name)
    for name, mt in container.mime_map.items():
        if mt and mt.startswith('image/'):
            name_lower = name.lower()
            if 'cover' in name_lower:
                return name
    return None

def process_epub(epub_path, output_path, replacement_path):
    shutil.copy(epub_path, output_path)
    try:
        container = get_container(output_path)
        cover_name = find_cover_image_name(container)
        if not cover_name:
            print(f"No cover found in {os.path.basename(epub_path)}, skipping")
            if os.path.exists(output_path):
                os.remove(output_path)
            return
        with open(replacement_path, 'rb') as f:
            new_cover_data = f.read()
        container.replace(cover_name, new_cover_data)
        container.commit()
        print(f"Replaced cover in {os.path.basename(output_path)}")
    except Exception as e:
        print(f"Failed to process {os.path.basename(epub_path)}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)

def main():
    if not os.path.isdir(epub_folder):
        print(f"EPUB folder not found: {epub_folder}")
        sys.exit(1)
    if not os.path.isdir(covers_folder):
        print(f"Covers folder not found: {covers_folder}")
        sys.exit(1)
    os.makedirs(output_folder, exist_ok=True)
    try:
        epub_files = [os.path.join(epub_folder, f) for f in os.listdir(epub_folder) if f.lower().endswith('.epub')]
    except FileNotFoundError:
        print(f"The folder '{epub_folder}' does not exist.")
        return
    if not epub_files:
        print("No EPUB files found")
        return
    success_count = 0
    skip_count = 0
    for epub_path in epub_files:
        epub_basename = os.path.basename(epub_path)
        epub_stem = os.path.splitext(epub_basename)[0]
        replacement_path = os.path.join(covers_folder, epub_stem + '.jpg')
        if not os.path.exists(replacement_path):
            replacement_path = os.path.join(covers_folder, epub_stem + '.png')
        if not os.path.exists(replacement_path):
            print(f"No replacement image found for {epub_basename}, skipping")
            skip_count += 1
            continue
        output_path = os.path.join(output_folder, epub_basename)
        process_epub(epub_path, output_path, replacement_path)
        success_count += 1
    print(f"\nProcessed {len(epub_files)} files: {success_count} covers replaced, {skip_count} skipped")

if __name__ == "__main__":
    main()

