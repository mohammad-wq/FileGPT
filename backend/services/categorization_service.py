"""
AI-Powered File Categorization Service
Uses LLM to intelligently categorize and organize files based on natural language criteria.
"""

import os
from typing import List, Dict, Optional
import ollama

from services import searchEngine, metadata_db


def categorize_files(
    category_description: str,
    search_path: Optional[str] = None,
    max_files: int = 100
) -> Dict:
    """
    Find files matching a category description using AI.
    
    Args:
        category_description: Natural language description (e.g., "sorting algorithms")
        search_path: Optional path to limit search scope
        max_files: Maximum number of files to evaluate
        
    Returns:
        Dictionary with matched files and their relevance scores
    """
    # Step 1: Use hybrid search to find potentially relevant files
    search_results = searchEngine.hybrid_search(category_description, k=max_files)
    
    if not search_results:
        return {
            "category": category_description,
            "matched_files": [],
            "total_evaluated": 0
        }
    
    # Step 2: Group results by source file
    file_chunks = {}
    for result in search_results:
        source = result['source']
        if search_path and not source.startswith(search_path):
            continue
            
        if source not in file_chunks:
            file_chunks[source] = {
                'path': source,
                'summary': result.get('summary', ''),
                'chunks': [],
                'max_score': 0
            }
        
        file_chunks[source]['chunks'].append(result['content'])
        file_chunks[source]['max_score'] = max(
            file_chunks[source]['max_score'],
            result.get('score', 0)
        )
    
    # Step 3: Use LLM to classify each file
    matched_files = []
    
    for file_path, file_info in file_chunks.items():
        # Prepare context for LLM
        content_preview = '\n'.join(file_info['chunks'][:3])  # First 3 chunks
        
        is_match, confidence = _classify_file_with_llm(
            file_path=file_path,
            summary=file_info['summary'],
            content_preview=content_preview,
            category=category_description
        )
        
        if is_match:
            matched_files.append({
                'path': file_path,
                'filename': os.path.basename(file_path),
                'summary': file_info['summary'],
                'confidence': confidence,
                'search_score': file_info['max_score']
            })
    
    # Sort by confidence
    matched_files.sort(key=lambda x: x['confidence'], reverse=True)
    
    return {
        "category": category_description,
        "matched_files": matched_files,
        "total_evaluated": len(file_chunks),
        "total_matched": len(matched_files)
    }


def _classify_file_with_llm(
    file_path: str,
    summary: str,
    content_preview: str,
    category: str
) -> tuple[bool, float]:
    """
    Use LLM to determine if a file matches a category.
    
    Returns:
        (is_match, confidence_score)
    """
    prompt = f"""You are a file categorization assistant. Determine if the following file belongs to the category: "{category}"

File: {file_path}
Summary: {summary}

Content Preview:
{content_preview[:2000]}

Question: Does this file belong to the category "{category}"?

Respond in this EXACT format:
MATCH: [YES or NO]
CONFIDENCE: [0.0 to 1.0]
REASON: [brief explanation]

Response:"""
    
    try:
        response = ollama.chat(
            model="qwen2.5:0.5b",
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.2,  # Low temperature for consistent classification
                'num_predict': 100,
            }
        )
        
        result = response['message']['content'].strip()
        
        # Parse response
        is_match = 'MATCH: YES' in result.upper()
        
        # Extract confidence
        confidence = 0.5  # Default
        for line in result.split('\n'):
            if 'CONFIDENCE:' in line.upper():
                try:
                    confidence_str = line.split(':')[1].strip()
                    confidence = float(confidence_str)
                except:
                    pass
        
        return is_match, confidence
        
    except Exception as e:
        print(f"Error classifying file {file_path}: {e}")
        return False, 0.0


def auto_organize_by_category(
    category_description: str,
    destination_folder: str,
    search_path: Optional[str] = None,
    min_confidence: float = 0.6,
    dry_run: bool = False
) -> Dict:
    """
    Automatically organize files into a folder based on category.
    
    Args:
        category_description: What to categorize (e.g., "sorting algorithms")
        destination_folder: Where to move matching files
        search_path: Optional path to limit search
        min_confidence: Minimum confidence threshold (0.0-1.0)
        dry_run: If True, don't actually move files
        
    Returns:
        Dictionary with operation results
    """
    # Find matching files
    categorization_result = categorize_files(
        category_description=category_description,
        search_path=search_path,
        max_files=100
    )
    
    # Filter by confidence
    files_to_move = [
        f for f in categorization_result['matched_files']
        if f['confidence'] >= min_confidence
    ]
    
    if not files_to_move:
        return {
            "status": "no_matches",
            "message": f"No files found matching '{category_description}' with confidence >= {min_confidence}",
            "evaluated": categorization_result['total_evaluated'],
            "files_moved": []
        }
    
    # Create destination folder if needed
    if not dry_run and not os.path.exists(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)
    
    # Move files
    moved_files = []
    errors = []
    
    for file_info in files_to_move:
        source_path = file_info['path']
        filename = file_info['filename']
        dest_path = os.path.join(destination_folder, filename)
        
        # Handle name conflicts
        if os.path.exists(dest_path) and dest_path != source_path:
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(destination_folder, f"{base}_{counter}{ext}")
                counter += 1
        
        try:
            if not dry_run and source_path != dest_path:
                import shutil
                shutil.move(source_path, dest_path)
                
                # Update search index
                searchEngine.delete_file_from_index(source_path)
                searchEngine.index_file_pipeline(dest_path)
            
            moved_files.append({
                'original_path': source_path,
                'new_path': dest_path,
                'confidence': file_info['confidence'],
                'dry_run': dry_run
            })
            
        except Exception as e:
            errors.append({
                'file': source_path,
                'error': str(e)
            })
    
    return {
        "status": "success",
        "category": category_description,
        "destination": destination_folder,
        "evaluated": categorization_result['total_evaluated'],
        "matched": len(files_to_move),
        "files_moved": moved_files,
        "errors": errors,
        "dry_run": dry_run
    }


def suggest_categories(file_paths: List[str]) -> List[Dict]:
    """
    Suggest categories for a list of files using LLM.
    
    Args:
        file_paths: List of file paths to categorize
        
    Returns:
        List of suggested categories with files
    """
    # Get summaries for all files
    file_summaries = []
    for path in file_paths[:50]:  # Limit to 50 files
        summary = metadata_db.get_summary(path)
        if summary:
            file_summaries.append({
                'path': path,
                'filename': os.path.basename(path),
                'summary': summary
            })
    
    if not file_summaries:
        return []
    
    # Build prompt for LLM
    files_text = '\n'.join([
        f"- {f['filename']}: {f['summary']}"
        for f in file_summaries[:20]
    ])
    
    prompt = f"""Analyze these files and suggest 3-5 meaningful categories to organize them:

{files_text}

Provide category suggestions in this format:
1. [Category Name]: [Brief description]
2. [Category Name]: [Brief description]
...

Categories:"""
    
    try:
        response = ollama.chat(
            model="qwen2.5:0.5b",
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.5,
                'num_predict': 300,
            }
        )
        
        result = response['message']['content'].strip()
        
        # Parse categories
        categories = []
        for line in result.split('\n'):
            line = line.strip()
            if line and any(line.startswith(f"{i}.") for i in range(1, 10)):
                # Extract category name
                parts = line.split(':', 1)
                if len(parts) == 2:
                    category_name = parts[0].split('.', 1)[1].strip()
                    description = parts[1].strip()
                    categories.append({
                        'category': category_name,
                        'description': description
                    })
        
        return categories
        
    except Exception as e:
        print(f"Error suggesting categories: {e}")
        return []
