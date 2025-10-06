import sys
import os
import json
import base64
from pathlib import Path
import logging

# Docling for general parsing and structured output
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.pipeline_options import PipelineOptions
    # Try to import OCR options, but handle if not available
    try:
        from docling.datamodel.pipeline_options import TesseractOcrOptions
        HAS_OCR_OPTIONS = True
    except ImportError:
        HAS_OCR_OPTIONS = False
        logging.warning("TesseractOcrOptions not available in this Docling version")
    HAS_DOCLING = True
except ImportError:
    HAS_DOCLING = False
    logging.warning("Docling not available, skipping Docling-based extraction")

# Specific libraries for image extraction
try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    logging.warning("python-docx not available")

try:
    from openpyxl import load_workbook
    from openpyxl.drawing.image import Image as ExcelDrawingImage
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    logging.warning("openpyxl not available")

try:
    import fitz  # PyMuPDF for PDF image extraction
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logging.warning("PyMuPDF not available")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logging.warning("PIL/Pillow not available")

import shutil

# Configure logging to go to stderr so stdout is clean for JSON output
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)

def extract_content_and_images(file_path, file_type, output_image_dir):
    """
    Parses a document, extracts text chunks and images, and returns structured data.
    """
    text_content = ""
    extracted_images_paths = []
    
    # Ensure output directory exists
    Path(output_image_dir).mkdir(parents=True, exist_ok=True)
    logging.info(f"Created/verified output directory: {output_image_dir}")

    try:
        logging.info(f"Processing file: {file_path} with type: {file_type}")
        
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            logging.error(f"File does not exist: {file_path}")
            return {"text_content": "", "extracted_images": []}
        
        file_size = os.path.getsize(file_path)
        logging.info(f"File size: {file_size} bytes")

        # --- Use Docling for primary text/structure extraction ---
        if HAS_DOCLING and file_type in [
            'application/pdf', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/html', 'text/markdown', 'text/plain'
        ]:
            try:
                # Try different ways to initialize DocumentConverter based on version
                doc_converter = None
                
                # Method 1: Try with pipeline_options (newer versions)
                try:
                    pipeline_options = PipelineOptions()
                    if HAS_OCR_OPTIONS:
                        try:
                            pipeline_options.ocr_options = TesseractOcrOptions()
                        except Exception as ocr_e:
                            logging.warning(f"Could not configure OCR options: {ocr_e}")
                    doc_converter = DocumentConverter(pipeline_options=pipeline_options)
                    logging.info("DocumentConverter initialized with pipeline_options")
                except Exception as e1:
                    logging.warning(f"Failed to initialize DocumentConverter with pipeline_options: {e1}")
                    
                    # Method 2: Try without pipeline_options (older versions)
                    try:
                        doc_converter = DocumentConverter()
                        logging.info("DocumentConverter initialized without pipeline_options")
                    except Exception as e2:
                        logging.error(f"Failed to initialize DocumentConverter: {e2}")
                        doc_converter = None
                
                if doc_converter:
                    logging.info(f"Attempting to convert {file_path} with Docling...")
                    result = doc_converter.convert(file_path)
                    
                    if result and result.document:
                        markdown_content = result.document.export_to_markdown()
                        text_content = markdown_content
                        logging.info(f"Docling successfully extracted markdown content (length: {len(text_content)})")

                        # Extract images directly from Docling's output if available
                        if hasattr(result.document, 'images') and result.document.images:
                            logging.info(f"Docling found {len(result.document.images)} images")
                            for idx, img_item in enumerate(result.document.images):
                                if hasattr(img_item, 'base64_content') and img_item.base64_content:
                                    try:
                                        image_bytes = base64.b64decode(img_item.base64_content)
                                        image_ext = img_item.image_type.split('/')[-1] if hasattr(img_item, 'image_type') and img_item.image_type else 'png'
                                        image_name = f"docling_img_{os.path.basename(file_path).replace('.', '_')}_{idx}.{image_ext}"
                                        image_path = os.path.join(output_image_dir, image_name)
                                        
                                        with open(image_path, 'wb') as f:
                                            f.write(image_bytes)
                                        extracted_images_paths.append(image_path)
                                        logging.info(f"Docling extracted image: {image_name} (size: {len(image_bytes)} bytes)")
                                    except Exception as img_save_e:
                                        logging.error(f"Failed to save Docling extracted image {idx}: {img_save_e}")
                        else:
                            logging.info(f"Docling document has no images attribute or no images found")
                    else:
                        logging.warning(f"Docling conversion returned no document for {file_path}")
                else:
                    logging.warning("Could not initialize DocumentConverter, skipping Docling extraction")

            except Exception as e:
                logging.error(f"Docling parsing error for {file_path} ({file_type}): {e}", exc_info=True)

        # --- Enhanced DOCX Image Extraction ---
        if HAS_DOCX and file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            try:
                logging.info("Starting DOCX image extraction...")
                doc = DocxDocument(file_path)
                
                # If Docling didn't get text, extract from paragraphs
                if not text_content:
                    doc_text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
                    text_content = "\n\n".join(doc_text_parts)
                    logging.info(f"Extracted text from DOCX using python-docx (length: {len(text_content)})")

                # Check relationships for images
                logging.info(f"Found {len(doc.part.rels)} relationships in DOCX")
                image_count = 0
                
                for rel_id, rel in doc.part.rels.items():
                    logging.debug(f"Relationship {rel_id}: {rel.target_ref}")
                    if "image" in rel.target_ref.lower():
                        try:
                            image_part = rel.target_part
                            image_bytes = image_part.blob
                            
                            # Try to determine image extension from content type or filename
                            image_ext = "png"  # default
                            if hasattr(image_part, 'content_type'):
                                if 'jpeg' in image_part.content_type.lower():
                                    image_ext = "jpg"
                                elif 'png' in image_part.content_type.lower():
                                    image_ext = "png"
                                elif 'gif' in image_part.content_type.lower():
                                    image_ext = "gif"
                            
                            image_name = f"word_img_{os.path.basename(file_path).replace('.', '_')}_{image_count}.{image_ext}"
                            image_path = os.path.join(output_image_dir, image_name)
                            
                            with open(image_path, "wb") as f:
                                f.write(image_bytes)
                            extracted_images_paths.append(image_path)
                            image_count += 1
                            logging.info(f"DOCX extracted image: {image_name} (size: {len(image_bytes)} bytes)")
                        except Exception as img_e:
                            logging.error(f"Error extracting image from relationship {rel_id}: {img_e}")
                
                logging.info(f"Total DOCX images extracted: {image_count}")
                            
            except Exception as e:
                logging.error(f"Error extracting from DOCX {file_path}: {e}", exc_info=True)

        # --- Enhanced XLSX Image Extraction ---
        elif HAS_OPENPYXL and file_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
            try:
                logging.info("Starting XLSX image extraction...")
                workbook = load_workbook(file_path, data_only=False)
                
                # If Docling didn't get text, extract from cells
                if not text_content:
                    excel_text_parts = []
                    for sheet_name in workbook.sheetnames:
                        sheet = workbook[sheet_name]
                        sheet_text = []
                        for row in sheet.iter_rows():
                            row_text = []
                            for cell in row:
                                if cell.value is not None:
                                    row_text.append(str(cell.value))
                            if row_text:
                                sheet_text.append("\t".join(row_text))
                        if sheet_text:
                            excel_text_parts.append(f"Sheet: {sheet_name}\n" + "\n".join(sheet_text))
                    text_content = "\n\n".join(excel_text_parts)
                    logging.info(f"Extracted text from XLSX using openpyxl (length: {len(text_content)})")

                total_images = 0
                for sheet_name in workbook.sheetnames:
                    logging.info(f"Processing sheet: {sheet_name}")
                    sheet = workbook[sheet_name]
                    
                    # Check for drawings/images in multiple ways
                    sheet_images = 0
                    
                    # Method 1: Check _images attribute first (more direct)
                    if hasattr(sheet, '_images') and sheet._images:
                        logging.info(f"Sheet {sheet_name} has _images attribute with {len(sheet._images)} items")
                        for i, img in enumerate(sheet._images):
                            try:
                                image_bytes = None
                                if hasattr(img, '_data'):
                                    image_bytes = img._data()
                                elif hasattr(img, 'ref'):
                                    # Try to get image data from workbook parts
                                    try:
                                        image_part = workbook._archive.read(img.ref)
                                        image_bytes = image_part
                                    except:
                                        logging.warning(f"Could not read image from ref: {img.ref}")
                                
                                if image_bytes:
                                    # Determine extension from image content
                                    image_ext = "png"  # default
                                    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                                        image_ext = "png"
                                    elif image_bytes.startswith(b'\xff\xd8\xff'):
                                        image_ext = "jpg"
                                    elif image_bytes.startswith(b'GIF'):
                                        image_ext = "gif"
                                    
                                    image_name = f"excel_img_{os.path.basename(file_path).replace('.', '_')}_{sheet_name}_{i}.{image_ext}"
                                    image_path = os.path.join(output_image_dir, image_name)
                                    
                                    with open(image_path, "wb") as f:
                                        f.write(image_bytes)
                                    extracted_images_paths.append(image_path)
                                    sheet_images += 1
                                    total_images += 1
                                    logging.info(f"XLSX extracted image: {image_name} (size: {len(image_bytes)} bytes)")
                                else:
                                    logging.warning(f"Could not extract image data from _images[{i}]")
                            except Exception as img_e:
                                logging.error(f"Error extracting image {i} from _images: {img_e}")
                    
                    # Method 2: Check _drawing attribute
                    if hasattr(sheet, '_drawing') and sheet._drawing:
                        logging.info(f"Sheet {sheet_name} has _drawing attribute")
                        
                        # Try accessing via drawing anchors
                        if hasattr(sheet._drawing, '_anchors') and sheet._drawing._anchors:
                            logging.info(f"Found {len(sheet._drawing._anchors)} anchors in drawing")
                            for i, anchor in enumerate(sheet._drawing._anchors):
                                try:
                                    # Try to find image data in anchor
                                    if hasattr(anchor, 'pic') and anchor.pic:
                                        pic = anchor.pic
                                        
                                        if hasattr(pic, 'blipFill') and pic.blipFill:
                                            blip_fill = pic.blipFill
                                            if hasattr(blip_fill, 'blip') and blip_fill.blip:
                                                blip = blip_fill.blip
                                                
                                                # Try different ways to get image data
                                                image_bytes = None
                                                if hasattr(blip, '_data'):
                                                    image_bytes = blip._data()
                                                elif hasattr(blip, 'embed') and blip.embed:
                                                    # Try to get from workbook archive
                                                    try:
                                                        rel_target = None
                                                        for rel in sheet._drawing.part.rels.values():
                                                            if rel.rId == blip.embed:
                                                                rel_target = rel.target_ref
                                                                break
                                                        
                                                        if rel_target:
                                                            image_bytes = workbook._archive.read(rel_target)
                                                    except Exception as rel_e:
                                                        logging.warning(f"Could not read image from relationship: {rel_e}")
                                                
                                                if image_bytes:
                                                    # Determine extension
                                                    image_ext = "png"
                                                    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                                                        image_ext = "png"
                                                    elif image_bytes.startswith(b'\xff\xd8\xff'):
                                                        image_ext = "jpg"
                                                    elif image_bytes.startswith(b'GIF'):
                                                        image_ext = "gif"
                                                    
                                                    image_name = f"excel_anchor_img_{os.path.basename(file_path).replace('.', '_')}_{sheet_name}_{i}.{image_ext}"
                                                    image_path = os.path.join(output_image_dir, image_name)
                                                    
                                                    with open(image_path, "wb") as f:
                                                        f.write(image_bytes)
                                                    extracted_images_paths.append(image_path)
                                                    sheet_images += 1
                                                    total_images += 1
                                                    logging.info(f"XLSX extracted anchor image: {image_name} (size: {len(image_bytes)} bytes)")
                                except Exception as anchor_e:
                                    logging.error(f"Error extracting from anchor {i}: {anchor_e}")
                    
                    logging.info(f"Sheet {sheet_name}: extracted {sheet_images} images")
                
                logging.info(f"Total XLSX images extracted: {total_images}")
                
            except Exception as e:
                logging.error(f"Error extracting from XLSX {file_path}: {e}", exc_info=True)

        # --- Enhanced PDF Image Extraction ---
        elif HAS_PYMUPDF and file_type == 'application/pdf':
            try:
                logging.info("Starting PDF image extraction...")
                doc = fitz.open(file_path)
                total_images = 0
                
                logging.info(f"PDF has {len(doc)} pages")
                
                for page_index in range(len(doc)):
                    page = doc.load_page(page_index)
                    image_list = page.get_images(full=True)
                    logging.info(f"Page {page_index + 1}: found {len(image_list)} images")
                    
                    for image_index, img in enumerate(image_list, start=1):
                        try:
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            if base_image:
                                image_bytes = base_image["image"]
                                image_ext = base_image["ext"]
                                image_name = f"pdf_img_{os.path.basename(file_path).replace('.', '_')}_page_{page_index+1}_{image_index}.{image_ext}"
                                image_path = os.path.join(output_image_dir, image_name)
                                
                                with open(image_path, "wb") as f:
                                    f.write(image_bytes)
                                extracted_images_paths.append(image_path)
                                total_images += 1
                                logging.info(f"PDF extracted image: {image_name} (size: {len(image_bytes)} bytes)")
                            else:
                                logging.warning(f"Could not extract image {image_index} from page {page_index + 1}")
                        except Exception as img_e:
                            logging.error(f"Error extracting image {image_index} from page {page_index + 1}: {img_e}")
                
                logging.info(f"Total PDF images extracted: {total_images}")
                doc.close()
                
            except Exception as e:
                logging.error(f"Error extracting from PDF {file_path}: {e}", exc_info=True)

        # --- Handle direct image files ---
        elif file_type.startswith('image/'):
            try:
                logging.info(f"Processing direct image file: {file_path}")
                image_ext = file_type.split('/')[-1]
                image_name = f"uploaded_image_{os.path.basename(file_path).replace('.', '_')}.{image_ext}"
                final_image_path = os.path.join(output_image_dir, image_name)
                
                shutil.copy(file_path, final_image_path) 
                extracted_images_paths.append(final_image_path)
                logging.info(f"Direct image file processed: {image_name}")
                
            except Exception as e:
                logging.error(f"Error processing direct image file {file_path}: {e}", exc_info=True)
                
        # --- Handle CSV files ---
        elif file_type == 'text/csv':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not text_content:
                    text_content = content
                logging.info(f"Read CSV file: {file_path} (length: {len(content)})")
            except Exception as e:
                logging.error(f"Could not read CSV file {file_path}: {e}")

        # --- Handle other text files ---
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not text_content:
                    text_content = content
                logging.info(f"Read generic text file: {file_path} (length: {len(content)})")
            except Exception as e:
                logging.error(f"Could not read as generic text file {file_path}: {e}")

    except Exception as general_e:
        logging.error(f"An unexpected error occurred during extraction for {file_path}: {general_e}", exc_info=True)

    # Final summary
    logging.info(f"Extraction complete. Text length: {len(text_content)}, Images found: {len(extracted_images_paths)}")
    for img_path in extracted_images_paths:
        if os.path.exists(img_path):
            img_size = os.path.getsize(img_path)
            logging.info(f"Final image: {os.path.basename(img_path)} (size: {img_size} bytes)")
        else:
            logging.error(f"Image file not found: {img_path}")

    return {
        "text_content": text_content,
        "extracted_images": extracted_images_paths
    }

if __name__ == "__main__":
    if len(sys.argv) != 4:
        logging.error("Usage: python document_parser.py <file_path> <file_type> <output_image_dir>")
        print(json.dumps({"error": "Invalid arguments. Usage: python document_parser.py <file_path> <file_type> <output_image_dir>"}), file=sys.stdout)
        sys.exit(1)

    file_path = sys.argv[1]
    file_type = sys.argv[2]
    output_image_dir = sys.argv[3]

    try:
        result = extract_content_and_images(file_path, file_type, output_image_dir)
        print(json.dumps(result), file=sys.stdout)
    except Exception as e:
        logging.error(f"Failed to process document {file_path}: {e}", exc_info=True)
        print(json.dumps({"error": f"Internal Python script error: {str(e)}"}), file=sys.stdout)
        sys.exit(1)