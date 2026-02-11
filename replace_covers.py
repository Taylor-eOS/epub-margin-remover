from pathlib import Path, PurePosixPath
from lxml import etree
import zipfile
import shutil
import io
from PIL import Image

epub_folder = input('Folder with EPUB files: ')
covers_folder = input('Folder with cover files: ')
output_folder = epub_folder + 'new_covers'

def find_opf_path(z):
    try:
        with z.open('META-INF/container.xml') as f:
            tree = etree.parse(f)
            rootfile = tree.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
            if rootfile is not None:
                return rootfile.get('full-path')
    except Exception:
        pass
    for name in z.namelist():
        if name.lower().endswith('.opf'):
            return name
    return None

def resolve_href(opf_dir, href):
    return (PurePosixPath(opf_dir) / PurePosixPath(href)).as_posix()

def parse_opf(z, opf_path):
    with z.open(opf_path) as f:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(f, parser)
        root = tree.getroot()
        opf_ns = None
        for ns in (root.nsmap or {}).values():
            if ns and 'opf' in ns:
                opf_ns = ns
                break
        if opf_ns is None:
            opf_ns = 'http://www.idpf.org/2007/opf'
        ns = {'opf': opf_ns}
        manifest = {}
        manifest_el = root.find('opf:manifest', ns)
        if manifest_el is not None:
            for item in manifest_el.findall('opf:item', ns):
                iid = item.get('id')
                href = item.get('href')
                media = item.get('media-type')
                props = item.get('properties') or ''
                if iid and href:
                    manifest[iid] = {'href': href, 'media-type': media, 'properties': props}
        opf_dir = PurePosixPath(opf_path).parent.as_posix()
        return manifest, opf_dir, root, ns

def find_cover_path(z, manifest, opf_dir, root, ns):
    version = root.get('version') or '2.0'
    cover_zip_path = None
    cover_media = None
    if version.startswith('3'):
        for iid, item in manifest.items():
            props = item.get('properties', '')
            if props and 'cover-image' in props.split():
                cover_zip_path = resolve_href(opf_dir, item['href'])
                cover_media = item['media-type']
                break
    if not cover_zip_path:
        meta_cover = root.find('.//opf:meta[@name="cover"]', ns)
        if meta_cover is not None:
            cid = meta_cover.get('content')
            if cid and cid in manifest:
                cover_zip_path = resolve_href(opf_dir, manifest[cid]['href'])
                cover_media = manifest[cid]['media-type']
    if not cover_zip_path:
        guide = root.find('opf:guide', ns)
        if guide is not None:
            for ref in guide.findall('opf:reference', ns):
                if ref.get('type') == 'cover':
                    href = ref.get('href')
                    if href:
                        cover_zip_path = resolve_href(opf_dir, href.split('#')[0])
                        break
    if not cover_zip_path:
        candidates = []
        for name in z.namelist():
            p = PurePosixPath(name)
            if p.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                if p.name.lower().startswith('cover.'):
                    candidates.append(name)
        if candidates:
            candidates.sort(key=len)
            cover_zip_path = candidates[0]
    return cover_zip_path, cover_media

def process_epub(epub_path, output_path, replacement_path):
    shutil.copy(epub_path, output_path)
    with zipfile.ZipFile(epub_path, 'r') as z:
        opf_path = find_opf_path(z)
        if opf_path is None:
            print(f"No OPF found in {epub_path.name}, copied original")
            return
        manifest, opf_dir, root, ns = parse_opf(z, opf_path)
        cover_zip_path, cover_media = find_cover_path(z, manifest, opf_dir, root, ns)
        if cover_zip_path is None:
            print(f"No cover detected in {epub_path.name}, copied original")
            return
        if not replacement_path.exists():
            print(f"No replacement image for {epub_path.name}, copied original")
            return
        try:
            img = Image.open(replacement_path)
            media_to_format = {
                'image/jpeg': 'JPEG',
                'image/jpg': 'JPEG',
                'image/png': 'PNG',
                'image/gif': 'GIF'
            }
            fmt = media_to_format.get(cover_media, 'JPEG')
            if fmt == 'JPEG':
                if img.mode in ('RGBA', 'LA', 'PA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
            bytes_io = io.BytesIO()
            save_kwargs = {}
            if fmt == 'JPEG':
                save_kwargs = {'quality': 95, 'optimize': True}
            elif fmt == 'PNG':
                save_kwargs = {'optimize': True}
            img.save(bytes_io, format=fmt, **save_kwargs)
            new_cover_data = bytes_io.getvalue()
        except Exception as e:
            print(f"Failed to process replacement image for {epub_path.name}: {e}, copied original")
            return
        tmp_path = output_path.with_suffix('.tmp')
        try:
            with zipfile.ZipFile(epub_path, 'r') as zin:
                with zipfile.ZipFile(tmp_path, 'w') as zout:
                    for item in zin.infolist():
                        if item.filename == cover_zip_path:
                            zout.writestr(item, new_cover_data)
                        else:
                            zout.writestr(item, zin.read(item.filename))
            shutil.move(tmp_path, output_path)
            print(f"Replaced cover in {output_path.name}")
        except Exception as e:
            print(f"Failed to write modified EPUB for {epub_path.name}: {e}")
            if tmp_path.exists():
                tmp_path.unlink()

def main():
    p = Path(epub_folder).expanduser().resolve()
    c = Path(covers_folder).expanduser().resolve()
    out_p = Path(output_folder).expanduser().resolve()
    if not p.is_dir():
        print(f"EPUB folder not found: {p}")
        return
    if not c.is_dir():
        print(f"Covers folder not found: {c}")
        return
    out_p.mkdir(parents=True, exist_ok=True)
    epub_paths = sorted(p.rglob('*.epub'))
    if not epub_paths:
        print("No EPUB files found")
        return
    success_count = 0
    skip_count = 0
    for epub_path in epub_paths:
        replacement_path = c / (epub_path.stem + '.jpg')
        output_path = out_p / epub_path.name
        if replacement_path.exists():
            process_epub(epub_path, output_path, replacement_path)
            success_count += 1
        else:
            shutil.copy(epub_path, output_path)
            print(f"No replacement for {epub_path.name}, copied original")
            skip_count += 1
    print(f"\nProcessed {len(epub_paths)} files: {success_count} covers replaced, {skip_count} copied unchanged")

main()
