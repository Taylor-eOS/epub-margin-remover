import os
import zipfile
import io
from PIL import Image
from collections import defaultdict

epub_folder = "input_files"
output_folder = "output_files"

def find_all_substrings(text, substring, case_sensitive=True):
    positions = []
    if not case_sensitive:
        text_lower = text.lower()
        substring_lower = substring.lower()
        start = 0
        while True:
            pos = text_lower.find(substring_lower, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
    else:
        start = 0
        while True:
            pos = text.find(substring, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
    return positions

def replace_all_occurrences(text, old_str, new_str):
    if old_str not in text:
        return text, 0
    parts = []
    last_end = 0
    count = 0
    start = 0
    while True:
        pos = text.find(old_str, start)
        if pos == -1:
            break
        parts.append(text[last_end:pos])
        parts.append(new_str)
        count += 1
        last_end = pos + len(old_str)
        start = pos + len(old_str)
    parts.append(text[last_end:])
    return ''.join(parts), count

def process_image_to_jpeg(data):
    img = Image.open(io.BytesIO(data))
    if img.mode in ('RGBA', 'LA', 'PA', 'P'):
        if 'A' in img.mode:
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85, optimize=True)
    return output.getvalue()

def generate_replacement_variants(png_path):
    variants = set()
    variants.add(png_path)
    jpg_base = png_path[:-4]
    jpg_path = jpg_base + '.jpg'
    variants.add(jpg_path)
    if png_path != png_path.lower():
        variants.add(png_path.lower())
        variants.add((jpg_base + '.jpg').lower())
    if png_path != png_path.upper():
        variants.add(png_path.upper())
        variants.add((jpg_base + '.JPG').upper())
    parts = png_path.split('/')
    if len(parts) > 1:
        filename = parts[-1]
        variants.add(filename)
        variants.add(filename[:-4] + '.jpg')
    if '\\' in png_path:
        forward_slash = png_path.replace('\\', '/')
        variants.add(forward_slash)
        variants.add(forward_slash[:-4] + '.jpg')
    return list(variants)

def scan_for_png_references(text, png_filenames):
    references = defaultdict(list)
    for png_file in png_filenames:
        base_name = png_file.split('/')[-1]
        search_variants = [
            png_file,
            base_name,
            png_file.replace('/', '\\'),
            './' + png_file,
            '../' + png_file,
        ]
        path_parts = png_file.split('/')
        for i in range(len(path_parts)):
            partial = '/'.join(path_parts[i:])
            search_variants.append(partial)
        for variant in search_variants:
            positions = find_all_substrings(text, variant, case_sensitive=True)
            if positions:
                references[png_file].extend([(variant, pos) for pos in positions])
        positions_case_insensitive = find_all_substrings(text, png_file, case_sensitive=False)
        for pos in positions_case_insensitive:
            actual_text = text[pos:pos+len(png_file)]
            if actual_text not in [v for v, p in references[png_file]]:
                references[png_file].append((actual_text, pos))
    return references

def replace_png_with_jpg_in_text(text, png_filenames):
    modified_text = text
    total_replacements = 0
    replacement_log = []
    for png_file in sorted(png_filenames, key=len, reverse=True):
        jpg_file = png_file[:-4] + '.jpg'
        base_png = png_file.split('/')[-1]
        base_jpg = base_png[:-4] + '.jpg'
        replacement_pairs = []
        if png_file in modified_text:
            replacement_pairs.append((png_file, jpg_file))
        if base_png in modified_text and base_png != png_file:
            replacement_pairs.append((base_png, base_jpg))
        path_parts = png_file.split('/')
        for i in range(len(path_parts)):
            partial_png = '/'.join(path_parts[i:])
            partial_jpg = partial_png[:-4] + '.jpg'
            if partial_png in modified_text and partial_png not in [p[0] for p in replacement_pairs]:
                replacement_pairs.append((partial_png, partial_jpg))
        for old_ref, new_ref in replacement_pairs:
            new_text, count = replace_all_occurrences(modified_text, old_ref, new_ref)
            if count > 0:
                replacement_log.append(f"    Replaced '{old_ref}' -> '{new_ref}' ({count} times)")
                modified_text = new_text
                total_replacements += count
    return modified_text, total_replacements, replacement_log

def is_text_file(filename):
    text_extensions = [
        '.html', '.xhtml', '.htm', '.xml', '.css', '.opf', '.ncx',
        '.svg', '.txt', '.xht', '.json', '.js', '.smil'
    ]
    lower_name = filename.lower()
    for ext in text_extensions:
        if lower_name.endswith(ext):
            return True
    return False

def is_binary_file(filename):
    binary_extensions = [
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
        '.ttf', '.otf', '.woff', '.woff2',
        '.mp3', '.mp4', '.avi', '.mov',
        '.zip', '.epub'
    ]
    lower_name = filename.lower()
    for ext in binary_extensions:
        if lower_name.endswith(ext):
            return True
    return False

def process_epub(input_path, output_path):
    temp_output = output_path + '.tmp'
    print(f"\n{'='*80}")
    print(f"Processing: {input_path}")
    print(f"{'='*80}")
    png_files = []
    all_files = {}
    file_types = defaultdict(int)
    with zipfile.ZipFile(input_path, 'r') as inf:
        print("\nStep 1: Scanning ZIP contents...")
        for info in inf.infolist():
            filename = info.filename
            all_files[filename] = info
            lower_name = filename.lower()
            if lower_name.endswith('.png'):
                png_files.append(filename)
                print(f"  Found PNG: {filename} ({info.file_size} bytes)")
            ext_start = lower_name.rfind('.')
            if ext_start != -1:
                ext = lower_name[ext_start:]
                file_types[ext] += 1
        print(f"\nTotal files in EPUB: {len(all_files)}")
        print(f"PNG files found: {len(png_files)}")
        print("\nFile type distribution:")
        for ext, count in sorted(file_types.items()):
            print(f"  {ext}: {count}")
        if not png_files:
            print("\nNo PNG files found - nothing to convert")
            return
        print(f"\n{'='*80}")
        print("Step 2: Converting PNG images to JPEG...")
        print(f"{'='*80}")
        converted_images = {}
        conversion_stats = []
        for png_file in png_files:
            try:
                png_data = inf.read(png_file)
                jpeg_data = process_image_to_jpeg(png_data)
                jpg_filename = png_file[:-4] + '.jpg'
                converted_images[png_file] = {
                    'new_name': jpg_filename,
                    'data': jpeg_data,
                    'original_size': len(png_data),
                    'new_size': len(jpeg_data)
                }
                reduction = len(png_data) - len(jpeg_data)
                percent = (reduction / len(png_data) * 100) if len(png_data) > 0 else 0
                print(f"  {png_file}")
                print(f"    -> {jpg_filename}")
                print(f"    Original: {len(png_data):,} bytes, JPEG: {len(jpeg_data):,} bytes")
                print(f"    Reduction: {reduction:,} bytes ({percent:.1f}%)")
                conversion_stats.append({
                    'file': png_file,
                    'original': len(png_data),
                    'new': len(jpeg_data),
                    'reduction': reduction
                })
            except Exception as e:
                print(f"  ERROR converting {png_file}: {e}")
                import traceback
                traceback.print_exc()
        print(f"\n{'='*80}")
        print("Step 3: Scanning text files for PNG references...")
        print(f"{'='*80}")
        text_files_to_process = []
        for filename in all_files:
            if is_text_file(filename):
                text_files_to_process.append(filename)
        print(f"Found {len(text_files_to_process)} text files to scan")
        modified_text_files = {}
        total_text_replacements = 0
        for text_file in text_files_to_process:
            try:
                data = inf.read(text_file)
                text = data.decode('utf-8', errors='replace')
                modified_text, replacement_count, log = replace_png_with_jpg_in_text(text, png_files)
                if replacement_count > 0:
                    modified_text_files[text_file] = modified_text.encode('utf-8')
                    total_text_replacements += replacement_count
                    print(f"\n  {text_file}: {replacement_count} replacements")
                    for log_entry in log:
                        print(log_entry)
            except Exception as e:
                print(f"  ERROR processing {text_file}: {e}")
        print(f"\nTotal text files modified: {len(modified_text_files)}")
        print(f"Total replacements across all files: {total_text_replacements}")
        print(f"\n{'='*80}")
        print("Step 4: Writing output EPUB...")
        print(f"{'='*80}")
        with zipfile.ZipFile(temp_output, 'w') as outf:
            files_written = 0
            for info in inf.infolist():
                filename = info.filename
                if filename in png_files:
                    jpg_info = converted_images[filename]
                    new_filename = jpg_info['new_name']
                    jpeg_data = jpg_info['data']
                    compress_type = zipfile.ZIP_DEFLATED
                    if filename == 'mimetype' or filename.startswith('META-INF/'):
                        compress_type = zipfile.ZIP_STORED
                    outf.writestr(new_filename, jpeg_data, compress_type=compress_type)
                    files_written += 1
                    print(f"  Wrote: {new_filename}")
                elif filename in modified_text_files:
                    modified_data = modified_text_files[filename]
                    compress_type = zipfile.ZIP_DEFLATED
                    if filename == 'mimetype' or filename.startswith('META-INF/'):
                        compress_type = zipfile.ZIP_STORED
                    outf.writestr(filename, modified_data, compress_type=compress_type)
                    files_written += 1
                else:
                    original_data = inf.read(filename)
                    compress_type = zipfile.ZIP_DEFLATED
                    if filename == 'mimetype' or filename.startswith('META-INF/'):
                        compress_type = zipfile.ZIP_STORED
                    outf.writestr(filename, original_data, compress_type=compress_type)
                    files_written += 1
            print(f"\nTotal files written to output: {files_written}")
    os.replace(temp_output, output_path)
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    print(f"PNG files converted: {len(converted_images)}")
    print(f"Text files modified: {len(modified_text_files)}")
    print(f"Total string replacements: {total_text_replacements}")
    if conversion_stats:
        total_original = sum(s['original'] for s in conversion_stats)
        total_new = sum(s['new'] for s in conversion_stats)
        total_saved = total_original - total_new
        percent_saved = (total_saved / total_original * 100) if total_original > 0 else 0
        print(f"\nImage size reduction:")
        print(f"  Original total: {total_original:,} bytes")
        print(f"  JPEG total: {total_new:,} bytes")
        print(f"  Space saved: {total_saved:,} bytes ({percent_saved:.1f}%)")
    input_size = os.path.getsize(input_path)
    output_size = os.path.getsize(output_path)
    epub_saved = input_size - output_size
    epub_percent = (epub_saved / input_size * 100) if input_size > 0 else 0
    print(f"\nEPUB file size:")
    print(f"  Input: {input_size:,} bytes")
    print(f"  Output: {output_size:,} bytes")
    print(f"  Reduction: {epub_saved:,} bytes ({epub_percent:.1f}%)")
    print(f"{'='*80}\n")

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
    print(f"Found {len(epub_files)} EPUB file(s) to process")
    for epub_file in epub_files:
        epub_filename = os.path.basename(epub_file)
        output_path = os.path.join(output_folder, epub_filename)
        try:
            process_epub(epub_file, output_path)
        except Exception as e:
            print(f"\nFATAL ERROR processing {epub_file}:")
            print(f"  {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

