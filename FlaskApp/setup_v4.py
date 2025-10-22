"""
setup_v4.py - Setup script for Research V4
Creates necessary directories, files, and verifies installation
"""

import os
import sys
from pathlib import Path
import subprocess

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_step(step, text):
    print(f"\n{step}. {text}")
    print("-"*80)

def create_directory_structure():
    """Create all necessary directories"""
    print_step("1", "Creating Directory Structure")
    
    directories = [
        "services",
        "services/v4",
        "services/v4/config",
        "research_v4",
        "_posts"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {directory}")
        else:
            print(f"  ✓ Exists: {directory}")

def create_init_files():
    """Create __init__.py files"""
    print_step("2", "Creating __init__.py Files")
    
    init_files = [
        "services/__init__.py",
        "services/v4/__init__.py"
    ]
    
    init_content = {
        "services/__init__.py": '"""Services package initialization"""\n',
        "services/v4/__init__.py": '''"""Research V4 package initialization"""

from .ConfigManager import ConfigManager
from .FloraDatabase import FloraDatabase
from .Spider import EnhancedPlantSpider, search
from .RagSys import RAGSystem
from .ArtGenSys import EnhancedPlantArticleGenerator

__all__ = [
    'ConfigManager',
    'FloraDatabase',
    'EnhancedPlantSpider',
    'search',
    'RAGSystem',
    'EnhancedPlantArticleGenerator'
]

__version__ = '4.0.0'
'''
    }
    
    for init_file in init_files:
        path = Path(init_file)
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(init_content.get(init_file, '"""Package initialization"""\n'))
            print(f"  ✓ Created: {init_file}")
        else:
            print(f"  ✓ Exists: {init_file}")

def check_dependencies():
    """Check if required packages are installed"""
    print_step("3", "Checking Dependencies")
    
    required_packages = [
        'requests',
        'beautifulsoup4',
        'faiss-cpu',
        'sentence-transformers',
        'transformers',
        'torch',
        'PyPDF2',
        'wikipediaapi',
        'pandas'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(missing_packages):
    """Install missing dependencies"""
    if not missing_packages:
        print("\n  All dependencies are already installed!")
        return True
    
    print(f"\n  Found {len(missing_packages)} missing packages")
    response = input("\n  Install missing packages? (y/n): ")
    
    if response.lower() != 'y':
        print("  Skipping installation")
        return False
    
    print("\n  Installing packages...")
    try:
        subprocess.check_call([
            sys.executable, 
            "-m", 
            "pip", 
            "install", 
            *missing_packages
        ])
        print("\n  ✓ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  ❌ Installation failed: {e}")
        return False

def check_environment():
    """Check environment variables"""
    print_step("4", "Checking Environment Variables")
    
    api_key = os.getenv('SERP_API_KEY')
    
    if api_key:
        print(f"  ✓ SERP_API_KEY is set")
    else:
        print(f"  ⚠️  SERP_API_KEY is not set")
        print(f"     Set it with: export SERP_API_KEY='your_key_here'")
        print(f"     Get a key at: https://serpapi.com/")

def create_sample_database():
    """Create a sample database with schema"""
    print_step("5", "Creating Sample Database")
    
    db_path = Path("research_v4/flora_data.db")
    
    if db_path.exists():
        print(f"  ✓ Database already exists: {db_path}")
        return
    
    import sqlite3
    
    print(f"  Creating database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flora_plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            scientific_name TEXT,
            family TEXT,
            genus TEXT,
            species TEXT,
            url TEXT,
            complete INTEGER DEFAULT 0
        )
    ''')
    
    # Add sample data
    sample_plants = [
        ('Adiantum', 'Adiantum capillus-veneris', 'Pteridaceae', 'Adiantum', 'capillus-veneris', 'https://example.com/adiantum', 0),
        ('African Daisy', 'Osteospermum ecklonis', 'Asteraceae', 'Osteospermum', 'ecklonis', 'https://example.com/daisy', 0),
        ('Aloe', 'Aloe vera', 'Asphodelaceae', 'Aloe', 'vera', 'https://example.com/aloe', 0)
    ]
    
    cursor.executemany('''
        INSERT INTO flora_plants (title, scientific_name, family, genus, species, url, complete)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sample_plants)
    
    conn.commit()
    conn.close()
    
    print(f"  ✓ Database created with {len(sample_plants)} sample plants")

def verify_imports():
    """Verify that all modules can be imported"""
    print_step("6", "Verifying Module Imports")
    
    modules = [
        ('ConfigManager', 'services.v4.ConfigManager'),
        ('FloraDatabase', 'services.v4.FloraDatabase'),
        ('Spider', 'services.v4.Spider'),
        ('RagSys', 'services.v4.RagSys'),
        ('ArtGenSys', 'services.v4.ArtGenSys')
    ]
    
    all_good = True
    
    for name, module_path in modules:
        try:
            __import__(module_path)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name} - ERROR: {e}")
            all_good = False
    
    return all_good

def create_quick_start_script():
    """Create a quick start script"""
    print_step("7", "Creating Quick Start Script")
    
    script_content = '''#!/usr/bin/env python3
"""
quick_start.py - Quick start example for Research V4
"""

import sys
from services.v4.ConfigManager import ConfigManager
from services.v4.FloraDatabase import FloraDatabase

def main():
    print("="*80)
    print("Research V4 - Quick Start")
    print("="*80)
    
    # Initialize configuration
    print("\\nInitializing configuration...")
    config = ConfigManager(verbose=True)
    
    # Show configuration summary
    config.print_summary()
    
    # Test database connection
    print("\\nTesting database connection...")
    db = FloraDatabase(config)
    stats = db.get_statistics()
    
    print("\\n" + "="*80)
    print("✅ Setup Complete!")
    print("="*80)
    print("""
Next Steps:
1. Set your API key: export SERP_API_KEY='your_key'
2. Run full test: python test_v4.py
3. Generate article: python -c "from services.v4 import *; ..."
    """)

if __name__ == "__main__":
    main()
'''
    
    path = Path("quick_start.py")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"  ✓ Created: quick_start.py")

def print_summary(all_good, missing_packages):
    """Print final summary"""
    print_header("Setup Summary")
    
    if all_good and not missing_packages:
        print("\n✅ SUCCESS! Your Research V4 system is ready to use!")
        print("\nNext Steps:")
        print("  1. Set API key: export SERP_API_KEY='your_key'")
        print("  2. Test system: python quick_start.py")
        print("  3. Run full test: python test_v4.py")
    else:
        print("\n⚠️  Setup completed with warnings")
        if missing_packages:
            print(f"\n  Missing packages: {', '.join(missing_packages)}")
            print(f"  Install with: pip install {' '.join(missing_packages)}")
        if not all_good:
            print("\n  Some modules failed to import - check the errors above")

def main():
    """Main setup function"""
    print_header("Research V4 - Setup Script")
    print("\nThis script will set up your Research V4 environment\n")
    
    # Step 1: Create directories
    create_directory_structure()
    
    # Step 2: Create __init__.py files
    create_init_files()
    
    # Step 3: Check dependencies
    missing_packages = check_dependencies()
    
    # Step 4: Optionally install missing packages
    if missing_packages:
        install_dependencies(missing_packages)
        # Re-check after installation
        missing_packages = check_dependencies()
    
    # Step 5: Check environment
    check_environment()
    
    # Step 6: Create sample database
    create_sample_database()
    
    # Step 7: Verify imports
    all_good = verify_imports()
    
    # Step 8: Create quick start script
    create_quick_start_script()
    
    # Print summary
    print_summary(all_good, missing_packages)

if __name__ == "__main__":
    main()