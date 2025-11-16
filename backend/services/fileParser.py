import os
import pypdf
import docx

def get_file_content(file_path: str) -> str | None:
    """
    Takes a file path, extracts text content based on its extension.
    Returns:
        A string containing the file's text, or None if the file
        is unsupported or an error occurs.
    """
    try:
        # Get the file extension
        _, extension = os.path.splitext(file_path)
        extension = extension.lower()

        if extension == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        elif extension == ".pdf":
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text

        elif extension == ".docx":
            doc = docx.Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        
        else:
            print(f"Unsupported file type: {extension}")
            return None

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    # Create a dummy .txt file to test
    with open("test.txt", "w") as f:
        f.write("This is a test text file.")
    
    content = get_file_content("test.txt")
    print("--- TXT Content ---")
    print(content)