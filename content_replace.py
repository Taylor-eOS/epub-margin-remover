import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ebooklib import epub

class EPUBEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EPUB Search and Replace")
        self.root.geometry("700x500")  # Larger window size

        # Variables
        self.epub_path = None
        self.text_files = []
        self.selected_files = []

        # GUI Elements
        self.label = ttk.Label(root, text="Select an EPUB file to edit:")
        self.label.pack(pady=10)

        self.browse_button = ttk.Button(root, text="Browse", command=self.load_epub)
        self.browse_button.pack(pady=5)

        self.file_list_frame = ttk.LabelFrame(root, text="Select Files to Process")
        self.file_list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.search_label = ttk.Label(root, text="Search Text:")
        self.search_label.pack(pady=5)

        self.search_entry = ttk.Entry(root, width=60)  # Wider input field
        self.search_entry.pack(pady=5)

        self.replace_label = ttk.Label(root, text="Replacement Text:")
        self.replace_label.pack(pady=5)

        self.replace_entry = ttk.Entry(root, width=60)  # Wider input field
        self.replace_entry.pack(pady=5)

        self.process_button = ttk.Button(root, text="Process Selected Files", command=self.process_files)
        self.process_button.pack(pady=10)

    def load_epub(self):
        """Load an EPUB file and list its text-based files."""
        self.epub_path = filedialog.askopenfilename(filetypes=[("EPUB Files", "*.epub")])
        if not self.epub_path:
            return

        # Clear previous file list
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        # Load EPUB and identify text-based files
        self.text_files = []
        book = epub.read_epub(self.epub_path)
        for item in book.get_items():
            media_type = (item.media_type or '').lower()
            if media_type.startswith('text/') or media_type.endswith('+xml'):
                self.text_files.append(item.file_name)

        # Display files with checkboxes
        self.selected_files = []
        for file_name in self.text_files:
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.file_list_frame, text=file_name, variable=var)
            chk.pack(anchor="w")
            self.selected_files.append((file_name, var))

    def process_files(self):
        """Perform search-and-replace on selected files."""
        if not self.epub_path:
            messagebox.showerror("Error", "No EPUB file loaded.")
            return

        search_text = self.search_entry.get()
        replacement = self.replace_entry.get()

        if not search_text:
            messagebox.showerror("Error", "Search text cannot be empty.")
            return

        # Get selected files
        files_to_process = [file_name for file_name, var in self.selected_files if var.get()]
        if not files_to_process:
            messagebox.showerror("Error", "No files selected.")
            return

        try:
            # Load EPUB and process selected files
            book = epub.read_epub(self.epub_path)

            for item in book.get_items():
                if item.file_name in files_to_process:
                    content = item.get_content().decode('utf-8')
                    new_content = content.replace(search_text, replacement)  # Simple text replacement
                    item.set_content(new_content.encode('utf-8'))

            # Save the modified EPUB
            output_path = filedialog.asksaveasfilename(defaultextension=".epub", filetypes=[("EPUB Files", "*.epub")])
            if output_path:
                epub.write_epub(output_path, book, {})
                messagebox.showinfo("Success", f"Modified EPUB saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EPUBEditorApp(root)
    root.mainloop()
