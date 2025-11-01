import os
import sys
import collections

# --- Configuration ---
# Define the path where the script will create the folders and look for files.
# NOTE: This should be a test directory, NOT your main documents folder!
# We'll use a subfolder named 'test_automation' in the current working directory.
AUTOMATION_PATH = os.path.join(os.getcwd(), "test_automation")

# Define file extensions and their corresponding category folder names
FILE_CATEGORIES = {
    '.txt': 'Text_Documents',
    '.log': 'Text_Documents',
    '.py': 'Python_Scripts',
    '.csv': 'Data_Files',
    '.xlsx': 'Data_Files',
    '.doc': 'Documents',
    '.pdf': 'Documents',
}
# ---------------------

def setup_test_environment():
    """Creates the main test directory and some dummy files for demonstration."""
    print(f"1. Setting up test environment in: {AUTOMATION_PATH}")
    
    # Create the main directory if it doesn't exist
    if not os.path.exists(AUTOMATION_PATH):
        os.makedirs(AUTOMATION_PATH)
    
    # Create a few dummy files for organization and analysis
    dummy_files = {
        'report_draft.txt': "The model's performance was excellent. The test results show stability.",
        'setup.py': 'def main():\n    print("Automate")',
        'data_log.log': 'ERROR: File not found\nINFO: Success',
        'inventory.csv': 'A,B,C\n1,2,3',
    }
    
    # Write the dummy content to files
    for filename, content in dummy_files.items():
        filepath = os.path.join(AUTOMATION_PATH, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                print(f"   - Created dummy file: {filename}")
    
    print("-" * 30)

def organize_files():
    """Reads files in the directory and moves them to category folders."""
    print("2. Starting file organization...")
    
    # Iterate through all items in the target directory
    for item_name in os.listdir(AUTOMATION_PATH):
        source_path = os.path.join(AUTOMATION_PATH, item_name)
        
        # Skip if it's a directory (i.e., a category folder we created)
        if os.path.isdir(source_path):
            continue
        
        # Get the file extension (e.g., '.txt', '.py')
        # os.path.splitext returns ('filename', '.extension')
        _, extension = os.path.splitext(item_name)
        extension = extension.lower()
        
        # Check if the extension is in our categories list
        if extension in FILE_CATEGORIES:
            category_name = FILE_CATEGORIES[extension]
            target_folder = os.path.join(AUTOMATION_PATH, category_name)
            target_path = os.path.join(target_folder, item_name)
            
            # 1. Create the target folder if it doesn't exist
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)
                
            # 2. Move the file
            try:
                os.rename(source_path, target_path)
                print(f"   - Moved '{item_name}' to /{category_name}")
            except Exception as e:
                print(f"   - Error moving {item_name}: {e}")
                
    print("-" * 30)

def analyze_text_files():
    """Calculates the word frequency across all files in the Text_Documents folder."""
    text_folder = os.path.join(AUTOMATION_PATH, 'Text_Documents')
    if not os.path.exists(text_folder):
        print("3. Text_Documents folder not found. Skipping analysis.")
        return
        
    print(f"3. Analyzing word frequency in {os.path.basename(text_folder)}...")
    
    all_words = []
    total_files = 0
    
    for filename in os.listdir(text_folder):
        filepath = os.path.join(text_folder, filename)
        
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Simple text processing: convert to lowercase and split by whitespace
                    words = content.lower().split()
                    
                    # Filter out non-alphabetic words (simple cleaning)
                    words = [word.strip('.,!?-:;()[]"\'') for word in words if word.isalnum()]
                    
                    all_words.extend(words)
                    total_files += 1
                    
            except Exception as e:
                print(f"   - Error reading {filename}: {e}")

    if all_words:
        # Use Python's built-in Counter for fast frequency counting
        word_counts = collections.Counter(all_words)
        
        print(f"   - Total files analyzed: {total_files}")
        print(f"   - Total unique words found: {len(word_counts)}")
        print("\n   --- Top 5 Most Frequent Words ---")
        
        # Get the 5 most common words
        for word, count in word_counts.most_common(5):
            print(f"   - '{word}': {count} times")
    else:
        print("   - No words found for analysis.")
        
    print("-" * 30)

def main():
    """Main function to run the automation sequence."""
    
    print("--- PYTHON AUTOMATION STARTER ---")
    setup_test_environment()
    organize_files()
    analyze_text_files()
    print("Automation complete. Check the 'test_automation' folder for results!")

if __name__ == "__main__":
    main()
