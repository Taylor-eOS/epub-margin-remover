import os
import re
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
from collections import Counter

def count_tags_and_words(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    tags = soup.find_all()
    body = soup.find('body')
    if body:
        text = body.get_text(separator=' ')
    else:
        text = soup.get_text(separator=' ')
    words = re.findall(r'\w+', text)
    return len(tags), len(words)

def repeated_paragraph_penalty(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')]
    if not paragraphs:
        return 0
    counts = Counter(paragraphs)
    penalty = sum(count - 1 for count in counts.values() if count > 1)
    return penalty

def score_epub(epub_path):
    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        print(f"Error reading {os.path.basename(epub_path)}: {e}")
        return None
    total_tags = 0
    total_words = 0
    total_repeats = 0
    doc_items = list(book.get_items_of_type(ITEM_DOCUMENT))
    for item in doc_items:
        try:
            html = item.get_content().decode('utf-8')
        except Exception as e:
            continue
        tags, words = count_tags_and_words(html)
        total_tags += tags
        total_words += words
        total_repeats += repeated_paragraph_penalty(html)
    ratio = total_tags / total_words if total_words else 100
    score = ratio + (total_repeats * 0.1)
    return score, total_tags, total_words, total_repeats

def main():
    folder = "./input_files"
    results = []
    epub_files = [os.path.join(folder, f) for f in os.listdir(folder)
                  if f.lower().endswith('.epub')]
    if not epub_files:
        print("No EPUB files found in input_files.")
        return
    for epub_file in epub_files:
        result = score_epub(epub_file)
        if result is None:
            continue
        score, tags, words, repeats = result
        results.append((os.path.basename(epub_file), score, tags, words, repeats))
    results.sort(key=lambda x: x[1], reverse=True)
    print("Filename\tScore\tTags\tWords\tRepeated Paragraphs")
    for fname, score, tags, words, repeats in results:
        print(f"{fname}\t{score:.2f}\t{tags}\t{words}\t{repeats}")

if __name__ == "__main__":
    main()

