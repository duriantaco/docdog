import os
import logging
import sys

logger = logging.getLogger(__name__)

def find_project_root():
    markers = ['.git', 'pyproject.toml', 'setup.py', 'requirements.txt', 'package.json']
    current_dir = os.getcwd()  
    prev_dir = None
    while current_dir != prev_dir:
        for marker in markers:
            if os.path.exists(os.path.join(current_dir, marker)):
                return current_dir
        prev_dir = current_dir
        current_dir = os.path.dirname(current_dir)
    
    logger.error("No project markers found. Please run DocDog from a valid project directory.")
    logger.error(f"DocDog looks for these markers: {', '.join(markers)}")
    sys.exit(1)