import os
import shutil
from lxml import html, etree
from calibre.ebooks.oeb.polish.container import get_container

epub_folder = "./input_files"
output_folder = "./processed_epubs"
TARGET_MARGIN_TOP = "1em"
LARGE_FONT_THRESHOLD = 1.15

HEADER_INDICATORS = {
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    '.h1', '.h2', '.h3', '.h4', '.h5', '.h6',
    '.chapter-title', '.section-title', '.title', '.ch-title', '.ch-num',
    '.chapter', '.section', '.heading', '.header'
}

def is_likely_header_selector(selector):
    selector_lower = selector.lower().strip()
    for indicator in HEADER_INDICATORS:
        if indicator in selector_lower:
            return True
    return False

def strip_css_comments(css_text):
    result = []
    i = 0
    while i < len(css_text):
        if i < len(css_text) - 1 and css_text[i:i+2] == '/*':
            end = css_text.find('*/', i + 2)
            if end == -1:
                break
            i = end + 2
        else:
            result.append(css_text[i])
            i += 1
    return ''.join(result)

def parse_css_value_unit(value_str):
    value_str = value_str.strip()
    if not value_str or value_str == '0':
        return '0', ''
    for unit in ['rem', 'em', 'px', 'pt', '%', 'vh', 'vw', 'ch', 'ex']:
        if value_str.endswith(unit):
            num_part = value_str[:-len(unit)].strip()
            try:
                num_val = float(num_part)
                return str(num_val), unit
            except ValueError:
                return '0', ''
    try:
        num_val = float(value_str)
        return str(num_val), ''
    except ValueError:
        return '0', ''

def tokenize_css(css_text):
    css_text = strip_css_comments(css_text)
    tokens = []
    current = []
    in_string = None
    i = 0
    while i < len(css_text):
        char = css_text[i]
        if in_string:
            current.append(char)
            if char == in_string and (i == 0 or css_text[i-1] != '\\'):
                in_string = None
            i += 1
            continue
        if char in ('"', "'"):
            in_string = char
            current.append(char)
            i += 1
            continue
        if char in ('{', '}', ';'):
            if current:
                tokens.append(('text', ''.join(current).strip()))
                current = []
            tokens.append((char, char))
            i += 1
            continue
        current.append(char)
        i += 1
    if current:
        text = ''.join(current).strip()
        if text:
            tokens.append(('text', text))
    return tokens

def parse_css_rules(tokens):
    rules = []
    i = 0
    while i < len(tokens):
        if tokens[i][0] == 'text':
            selector_parts = []
            while i < len(tokens) and tokens[i][0] == 'text':
                selector_parts.append(tokens[i][1])
                i += 1
            selector = ' '.join(selector_parts)
            if i < len(tokens) and tokens[i][0] == '{':
                i += 1
                declarations = []
                while i < len(tokens) and tokens[i][0] != '}':
                    if tokens[i][0] == 'text' and tokens[i][1].strip():
                        declarations.append(tokens[i][1])
                    elif tokens[i][0] == ';':
                        pass
                    i += 1
                if i < len(tokens) and tokens[i][0] == '}':
                    i += 1
                rules.append({
                    'selector': selector,
                    'declarations': declarations,
                    'type': 'rule'
                })
            else:
                i += 1
        else:
            i += 1
    return rules

def extract_font_size_from_declarations(declarations):
    for decl in declarations:
        if ':' not in decl:
            continue
        prop, value = decl.split(':', 1)
        prop = prop.strip().lower()
        if prop == 'font-size':
            value = value.strip()
            if value.endswith(';'):
                value = value[:-1].strip()
            if value.endswith('!important'):
                value = value[:-10].strip()
            num, unit = parse_css_value_unit(value)
            if unit == 'em':
                try:
                    size = float(num)
                    return size
                except ValueError:
                    pass
    return None

def is_header_by_font_size(declarations):
    font_size = extract_font_size_from_declarations(declarations)
    if font_size is not None and font_size >= LARGE_FONT_THRESHOLD:
        return True
    return False

def is_header_rule(selector, declarations):
    if is_likely_header_selector(selector):
        return True
    if is_header_by_font_size(declarations):
        return True
    return False

def split_margin_shorthand(value):
    value = value.strip()
    if value.endswith('!important'):
        important = True
        value = value[:-10].strip()
    else:
        important = False
    parts = value.split()
    if len(parts) == 1:
        top = right = bottom = left = parts[0]
    elif len(parts) == 2:
        top = bottom = parts[0]
        right = left = parts[1]
    elif len(parts) == 3:
        top = parts[0]
        right = left = parts[1]
        bottom = parts[2]
    elif len(parts) == 4:
        top = parts[0]
        right = parts[1]
        bottom = parts[2]
        left = parts[3]
    else:
        top = right = bottom = left = '0'
    return top, right, bottom, left, important

def process_header_declaration(decl):
    if ':' not in decl:
        return decl, None
    prop, value = decl.split(':', 1)
    prop = prop.strip()
    value = value.strip()
    if value.endswith(';'):
        value = value[:-1].strip()
    prop_lower = prop.lower()
    if prop_lower == 'margin-top':
        return f"{prop}: {TARGET_MARGIN_TOP}", 'margin-top'
    elif prop_lower == 'margin':
        top, right, bottom, left, important = split_margin_shorthand(value)
        important_suffix = ' !important' if important else ''
        return f"margin: {TARGET_MARGIN_TOP} {right} {bottom} {left}{important_suffix}", 'margin'
    return f"{prop}: {value}", None

def process_header_declarations(declarations):
    processed = []
    has_margin_top = False
    has_margin = False
    for decl in declarations:
        new_decl, modified_type = process_header_declaration(decl)
        if modified_type == 'margin-top':
            has_margin_top = True
        elif modified_type == 'margin':
            has_margin = True
        processed.append(new_decl)
    if not has_margin_top and not has_margin:
        processed.append(f"margin-top: {TARGET_MARGIN_TOP}")
    return processed

def process_css_rules_for_headers(rules):
    output = []
    for rule in rules:
        if rule['type'] == 'rule':
            selector = rule['selector']
            declarations = rule['declarations']
            if is_header_rule(selector, declarations):
                processed_decls = process_header_declarations(declarations)
                output.append(f"{selector} {{")
                for decl in processed_decls:
                    output.append(f"    {decl};")
                output.append("}")
            else:
                output.append(f"{selector} {{")
                for decl in declarations:
                    if ':' in decl:
                        prop, value = decl.split(':', 1)
                        output.append(f"    {prop.strip()}: {value.strip()};")
                    else:
                        output.append(f"    {decl};")
                output.append("}")
    return '\n'.join(output)

def restore_header_margins_in_css(css_content):
    tokens = tokenize_css(css_content)
    rules = parse_css_rules(tokens)
    return process_css_rules_for_headers(rules)

def process_style_element(style_elem):
    if style_elem.text:
        original = style_elem.text
        processed = restore_header_margins_in_css(original)
        style_elem.text = processed
        return original != processed
    return False

def get_element_tag_name(elem):
    tag_name = elem.tag.lower() if isinstance(elem.tag, str) else ''
    if '}' in tag_name:
        tag_name = tag_name.split('}')[-1]
    return tag_name

def is_header_element(elem):
    tag_name = get_element_tag_name(elem)
    if tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        return True
    elem_class = elem.get('class', '')
    for indicator in HEADER_INDICATORS:
        if indicator.startswith('.') and indicator[1:] in elem_class.lower():
            return True
    return False

def process_style_attribute(elem):
    style_attr = elem.get('style')
    if not style_attr:
        return False
    if not is_header_element(elem):
        return False
    original = style_attr
    declarations = [d.strip() for d in style_attr.split(';') if d.strip()]
    processed_decls = process_header_declarations(declarations)
    new_style = '; '.join(processed_decls)
    elem.set('style', new_style)
    return original != new_style

def process_html_content(html_content):
    try:
        tree = html.fromstring(html_content)
    except:
        try:
            parser = etree.XMLParser(recover=True)
            tree = etree.fromstring(html_content.encode('utf-8'), parser)
        except:
            return html_content, False
    modified = False
    for style_elem in tree.xpath('//style'):
        if process_style_element(style_elem):
            modified = True
    for elem in tree.xpath('//*[@style]'):
        if process_style_attribute(elem):
            modified = True
    if modified:
        try:
            result = html.tostring(tree, encoding='unicode', method='html')
            return result, True
        except:
            try:
                result = etree.tostring(tree, encoding='unicode', method='xml')
                return result, True
            except:
                return html_content, False
    return html_content, False

def process_epub(input_path, output_path):
    shutil.copy(input_path, output_path)
    try:
        container = get_container(output_path)
        modified = False
        for name, mt in list(container.mime_map.items()):
            if mt == "text/css":
                css_text = container.raw_data(name, decode=True)
                new_css_text = restore_header_margins_in_css(css_text)
                if new_css_text != css_text:
                    container.replace(name, new_css_text)
                    modified = True
            elif mt in ("application/xhtml+xml", "text/html"):
                html_content = container.raw_data(name, decode=True)
                new_content, content_modified = process_html_content(html_content)
                if content_modified:
                    container.replace(name, new_content)
                    modified = True
        if modified:
            container.commit()
            print(f"Processed and saved: {output_path}")
        else:
            print(f"No header margins to restore in: {output_path}")
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

