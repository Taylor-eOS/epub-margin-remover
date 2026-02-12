import os
import shutil
from calibre.ebooks.oeb.polish.container import get_container
from lxml import etree, html

epub_folder = "input_files"
output_folder = "output_files"
HEADER_SELECTORS = {
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.h1', '.h2', '.h3', '.h4', '.h5', '.h6',
    '.chapter-title', '.section-title', '.title', '.ch-title', '.ch-num'}

QUOTE_SELECTORS = {'blockquote', '.blockquote', '.quote', '.epigraph'}

def get_exemption_type(selector):
    selector_lower = selector.lower().strip()
    for quote_sel in QUOTE_SELECTORS:
        if quote_sel in selector_lower:
            return 'quote'
    for header_sel in HEADER_SELECTORS:
        if header_sel in selector_lower:
            return 'header'
    return None

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

def normalize_text_indent(value):
    value = value.strip()
    if value.endswith('!important'):
        value = value[:-10].strip()
    value_lower = value.lower()
    if 'calc(' in value_lower or 'var(' in value_lower:
        return value
    num, unit = parse_css_value_unit(value)
    try:
        num_float = float(num)
        if num_float < 0:
            return '0'
        return num + unit
    except ValueError:
        return '0'

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

def process_declaration(decl, exempt_type):
    if ':' not in decl:
        return decl
    prop, value = decl.split(':', 1)
    prop = prop.strip()
    value = value.strip()
    if value.endswith(';'):
        value = value[:-1].strip()
    prop_lower = prop.lower()
    if prop_lower in ('margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
                      'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right'):
        if exempt_type == 'quote':
            return f"{prop}: {value}"
        elif exempt_type == 'header' and prop_lower == 'margin-top':
            return f"{prop}: {value}"
        else:
            return f"{prop}: 0 !important"
    if prop_lower == 'text-indent':
        if exempt_type == 'quote':
            return f"{prop}: {value}"
        new_value = normalize_text_indent(value)
        return f"{prop}: {new_value} !important"
    return f"{prop}: {value}"

def process_css_rules_list(rules):
    output = []
    for rule in rules:
        if rule['type'] == 'rule':
            selector = rule['selector']
            exempt_type = get_exemption_type(selector)
            output.append(f"{selector} {{")
            for decl in rule['declarations']:
                processed = process_declaration(decl, exempt_type)
                output.append(f"    {processed};")
            output.append("}")
    return '\n'.join(output)

def replace_margins_in_css(css_content):
    tokens = tokenize_css(css_content)
    rules = parse_css_rules(tokens)
    return process_css_rules_list(rules)

def process_style_element(style_elem):
    if style_elem.text:
        original = style_elem.text
        processed = replace_margins_in_css(original)
        style_elem.text = processed
        return original != processed
    return False

def process_style_attribute(elem):
    style_attr = elem.get('style')
    if not style_attr:
        return False
    original = style_attr
    tag_name = elem.tag.lower() if isinstance(elem.tag, str) else ''
    if '}' in tag_name:
        tag_name = tag_name.split('}')[-1]
    exempt_type = None
    if tag_name == 'blockquote':
        exempt_type = 'quote'
    elif tag_name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        exempt_type = 'header'
    else:
        elem_class = elem.get('class', '')
        for quote_sel in QUOTE_SELECTORS:
            if quote_sel.startswith('.') and quote_sel[1:] in elem_class.lower():
                exempt_type = 'quote'
                break
        if not exempt_type:
            for header_sel in HEADER_SELECTORS:
                if header_sel.startswith('.') and header_sel[1:] in elem_class.lower():
                    exempt_type = 'header'
                    break
    declarations = [d.strip() for d in style_attr.split(';') if d.strip()]
    processed_decls = []
    for decl in declarations:
        processed = process_declaration(decl, exempt_type)
        processed_decls.append(processed)
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
            if mt == "application/vnd.adobe-page-template+xml":
                container.remove_item(name)
                modified = True
            elif mt == "text/css":
                css_text = container.raw_data(name, decode=True)
                new_css_text = replace_margins_in_css(css_text)
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
            print(f"No CSS changes needed in: {output_path}")
            os.remove(output_path)
    except Exception as e:
        print(f"Failed to process {output_path}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)

def main():
    print('Run as: calibre-debug reduce_all_margins.py')
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

