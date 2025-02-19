import os

IGNORED_DIRS = {
    "__pycache__",
    "venv",
    ".git",
    ".streamlit",
    "attached_assets",
    ".idea",
    ".vscode",
    "node_modules",
    "build",
    "dist",
    "migrations"
}

IGNORED_FILES = {
    "setup.py",
    "__init__.py",
    "manage.py"
}

def consolidate_python_files(output_file="project_code.txt"):
    """
    Consolidates Python files from the root directory into a single text file.
    Excludes virtual environments, cache directories, and common non-relevant files.

    Parameters:
    output_file (str): The output file where the consolidated code will be saved.
    """
    root_dir = os.getcwd()

    with open(output_file, "w", encoding="utf-8") as outfile:
        for file in sorted(os.listdir(root_dir)):
            file_path = os.path.join(root_dir, file)

            if file.endswith(".py") and os.path.isfile(file_path) and file not in IGNORED_FILES:
                outfile.write(f"# File: {file}\n\n")
                with open(file_path, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read())
                    outfile.write("\n\n")

if __name__ == "__main__":
    consolidate_python_files()
