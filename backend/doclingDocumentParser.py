# backend/services/doclingDocumentParser.py

import os
import pypdf
import docx
import mimetypes

# --- Configuration ---

# Add any text-based extensions you want to support here
TEXT_BASED_EXTENSIONS = {
    # Code Files
    ".py", ".js", ".ts", ".c", ".cpp", ".h", ".hpp", ".java", ".go",
    ".cs", ".rb", ".php", ".swift", ".kt", ".rs", ".pl", ".sh", ".bat",
    
    # Web & Data
    ".html", ".css", ".scss", ".json", ".xml", ".yaml", ".yml", ".csv",
    ".toml", ".ini", ".sql",
    
    # Docs & Configs
    ".txt", ".md", ".log", ".rtf", ".tex", ".jsonl",
    
    # Config/Dot files
    ".dockerfile", ".gitignore", ".gitattributes", ".env"
}

# Complex formats that need special parsers
PDF_EXTENSIONS = {".pdf"}
WORD_EXTENSIONS = {".docx"}


def read_text_file(file_path: str) -> str | None:
    """
    Tries to read a file as text, handling different encodings.
    """
    try:
        # Try to read as UTF-8 first (most common)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            # If UTF-8 fails, try latin-1 (which can read any byte)
            print(f"[Parser] UTF-8 failed, trying latin-1 for {file_path}")
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"[Parser] Error reading {file_path} with latin-1: {e}")
            return None
    except Exception as e:
        print(f"[Parser] Error reading {file_path}: {e}")
        return None

def get_file_content(file_path: str) -> str | None:
    """
    Takes a file path, extracts text content based on its extension.
    Returns:
        A string containing the file's text, or None if the file
        is unsupported or an error occurs.
    """
    try:
        # Get the file extension. Handle dotfiles (e.g., .gitignore)
        _, extension = os.path.splitext(file_path)
        if not extension and os.path.basename(file_path).startswith('.'):
             # It's a dotfile (e.g., .gitignore)
             extension = os.path.basename(file_path)

        extension = extension.lower()

        # --- 1. Check for complex formats ---
        if extension in PDF_EXTENSIONS:
            print(f"[Parser] Processing PDF: {file_path}")
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text

        elif extension in WORD_EXTENSIONS:
            print(f"[Parser] Processing Word: {file_path}")
            doc = docx.Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        
        # --- 2. Check for all other text-based formats ---
        elif extension in TEXT_BASED_EXTENSIONS:
            print(f"[Parser] Processing Text/Code: {file_path}")
            return read_text_file(file_path)
        
        # --- 3. If not in any list, it's likely binary ---
        else:
            print(f"[Parser] Skipping unsupported/binary file: {file_path}")
            return None

    except Exception as e:
        print(f"[Parser] Critical error processing {file_path}: {e}")
        return None

# --- Example Usage (for testing this file directly) ---
if __name__ == "__main__":
    
    # Create dummy files for testing
    with open("test_script.py", "w") as f:
        f.write("def hello():\n  print('Hello World')")
        
    with open("test_doc.txt", "w") as f:
        f.write("This is a plain text file.")

    with open(".testconfig", "w") as f:
        f.write("API_KEY=12345")
        
    # Add .testconfig to our text list for this test
    TEXT_BASED_EXTENSIONS.add(".testconfig")

    print("--- Testing Python File ---")
    content_py = get_file_content("test_script.py")
    print(content_py)

    print("\n--- Testing Text File ---")
    content_txt = get_file_content("test_doc.txt")
    print(content_txt)
    
    print("\n--- Testing Dotfile ---")
    content_conf = get_file_content(".testconfig")
    print(content_conf)

    # Clean up
    os.remove("test_script.py")
    os.remove("test_doc.txt")
    os.remove(".testconfig")