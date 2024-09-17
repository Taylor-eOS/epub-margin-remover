# EPUB CSS Margin and Padding Remover

This is a Python script to process EPUB files by removing or resetting all CSS margin and padding properties within the EPUB's CSS files. This tool is useful for users who want consistent formatting across their EPUB files, in order to not waste screen real estate on an eReader.

## Features
- **Batch Processing**: Automatically processes all EPUB files in a specified directory.
- **Customizable**: Easily modify the script to change the margin and padding values.
- **Non-destructive**: Creates a new processed EPUB without altering the original file.

## Requirements
- Python 3.6 or higher
- Standard Python libraries: `os`, `zipfile`, `re`, `shutil`

## Installation
1. **Clone the Repository**
   ```bash
   git clone https://github.com/Taylor-eOS/epub-margins.git
   cd epub-margins
   ```
2. **(Optional) Create a Virtual Environment (No dependencies needed)**
   ```bash
   python -m venv epub-margins
   cd epub-margins  #On Windows: epub-margins\Scripts\activate
   source bin/activate
   ```

## Usage
1. **Place EPUB Files**
   Copy all the EPUB files you want to process into the root directory of the script.
2. **Run the Script**
   ```bash
   python epub-margins.py
   ```
3. **Processed Files**
   The processed EPUB files will be saved in the `processed_epubs` directory.

## How It Works
The script performs the following steps for each EPUB file:

1. **Extracts the EPUB**: Unzips the EPUB file into a temporary directory.
2. **Processes CSS Files**: Searches for all `.css` files and replaces margin and padding properties with `0 !important`.
3. **Repackages the EPUB**: Zips the processed files back into an EPUB format.
4. **Cleanup**: Removes the temporary directory used for processing.

## Customization
- **Changing Margin and Padding Values**
  If you want to set different values for margins and padding, modify the following variables at the top of the script:

  ```python
  NEW_MARGIN = "0 !important"
  NEW_PADDING = "0 !important"
  ```

## Troubleshooting
- **No EPUB Files Found**
  If you receive a "No EPUB files found" message, ensure that your EPUB files are in the same directory as the script.

- **Encoding Issues**
  If you encounter encoding errors, you may need to adjust the file reading/writing encoding in the script.

## License
This project is licensed under the MIT License.
