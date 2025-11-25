"""
Append categorization endpoints to main.py
"""

# New endpoints to add to main.py

new_endpoints = '''

# ============================================================================
# AI CATEGORIZATION ENDPOINTS
# ============================================================================

@app.post("/categorize")
async def categorize(request: CategorizeRequest):
    """
    Find files matching a category description using AI.
    
    Args:
        request: Contains category_description, optional search_path and max_files
        
    Returns:
        List of files that match the category with confidence scores
    """
    result = categorization_service.categorize_files(
        category_description=request.category_description,
        search_path=request.search_path,
        max_files=request.max_files
    )
    
    return result


@app.post("/organize")
async def organize(request: OrganizeRequest):
    """
    Automatically organize files into a folder based on category description.
    
    Example: "Put all sorting algorithms into C:\\\\SortingAlgorithms"
    
    Args:
        request: Contains category_description, destination_folder, and options
        
    Returns:
        Results of the organization operation including files moved
    """
    result = categorization_service.auto_organize_by_category(
        category_description=request.category_description,
        destination_folder=request.destination_folder,
        search_path=request.search_path,
        min_confidence=request.min_confidence,
        dry_run=request.dry_run
    )
    
    return result


@app.post("/suggest_categories")
async def suggest_categories(request: SuggestCategoriesRequest):
    """
    Get AI-suggested categories for organizing a list of files.
    
    Args:
        request: Contains list of file paths
        
    Returns:
        List of suggested categories with descriptions
    """
    suggestions =categorization_service.suggest_categories(request.file_paths)
    
    return {
        "suggestions": suggestions,
        "count": len(suggestions)
    }
'''

print(new_endpoints)
