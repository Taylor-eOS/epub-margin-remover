import os
import shutil

def find_threshold(entries):
    n = len(entries)
    best_gap = 0
    best_index = None
    for i in range(1, n):
        if i < 2 or (n - i) < 2: #Only consider gaps that don't isolate a single item on either side
            continue
        gap = entries[i][1] - entries[i-1][1]
        if gap > best_gap:
            best_gap = gap
            best_index = i
    if best_index is not None:
        return (entries[best_index][1] + entries[best_index - 1][1]) / 2
    return None

def main():
    log_file = "log.txt"
    input_dir = "./input_files"
    output_dir = "./bad_epubs"
    os.makedirs(output_dir, exist_ok=True)
    
    #Read entries from the log file.
    entries = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if ';' not in line:
                continue
            parts = line.strip().split(';')
            if len(parts) != 2:
                continue
            fname = parts[0]
            try:
                score = float(parts[1].replace(',', '.')) #Some locales use commas for decimal points.
                entries.append((fname, score))
            except ValueError:
                continue
    if not entries:
        print("No valid entries found in log.txt")
        return
    #Sort entries in ascending order by their score.
    entries.sort(key=lambda x: x[1])
    
    threshold = find_threshold(entries)
    if threshold is None:
        print("Could not determine a valid threshold; perhaps there are too few entries.")
        return
    print(f"Determined threshold: {threshold:.6f}")

    #Copy files with score above the threshold.
    selected_files = [fname for fname, score in entries if score > threshold]
    for fname in selected_files:
        src = os.path.join(input_dir, fname)
        dst = os.path.join(output_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    print(f"Copied {len(selected_files)} files to {output_dir}")

if __name__ == "__main__":
    main()

