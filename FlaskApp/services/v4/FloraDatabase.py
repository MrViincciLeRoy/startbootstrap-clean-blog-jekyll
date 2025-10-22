"""
FloraDatabase.py - Research V4
Plant database operations with configuration support
Database path loaded from ConfigManager
CORRECTED VERSION
"""

import sqlite3
import pandas as pd
from typing import List, Dict, Optional
import logging
from pathlib import Path

# FIXED: Use relative import
try:
    from .ConfigManager import ConfigManager
except ImportError:
    from services.v4.ConfigManager import ConfigManager

logger = logging.getLogger(__name__)


class FloraDatabase:
    """Database operations for flora data"""
    
    def __init__(self, config: ConfigManager = None, db_name: str = None):
        """
        Initialize database connection.
        
        Args:
            config: ConfigManager instance. If None, creates new instance.
            db_name: Database name. If None, uses value from config.
        """
        if config is None:
            config = ConfigManager()
        
        self.config = config
        
        # FIXED: Handle database path properly
        if db_name:
            self.db_name = db_name
        else:
            db_path = config.get_database_path()
            # Convert to Path object for proper handling
            self.db_name = str(Path(db_path))
        
        logger.info(f"Initialized FloraDatabase: {self.db_name}")
        
        # FIXED: Create database directory if it doesn't exist
        db_dir = Path(self.db_name).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")

    def get_all_scientific_names(self) -> List[tuple]:
        """Get all scientific names from the database."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, scientific_name, url
                FROM flora_plants
                WHERE scientific_name IS NOT NULL
                ORDER BY scientific_name
            """)

            results = cursor.fetchall()
            conn.close()

            return results
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return []

    def get_scientific_names_with_complete_data(self) -> List[tuple]:
        """Get scientific names only for complete entries."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, scientific_name, family, genus, url
                FROM flora_plants
                WHERE scientific_name IS NOT NULL
                AND complete = 0
                ORDER BY scientific_name
            """)

            results = cursor.fetchall()
            conn.close()

            return results
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return []

    def check_if_complete(self, scientific_name: str) -> Optional[bool]:
        """Check if a plant has complete data.

        Returns:
            True if complete = 1
            False if complete = 0
            None if scientific name not found
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT complete
                FROM flora_plants
                WHERE scientific_name = ?
            """, (scientific_name,))

            result = cursor.fetchone()
            conn.close()

            if result is None:
                return None

            return bool(result[0])
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return None

    def get_all_incomplete_plants(self) -> List[tuple]:
        """Get all plants with complete = 0 (incomplete data).

        Returns:
            List of tuples: (id, title, scientific_name, family, genus, url)
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, scientific_name, family, genus, url
                FROM flora_plants
                WHERE complete = 0
                ORDER BY scientific_name
            """)

            results = cursor.fetchall()
            conn.close()

            return results
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return []

    def search_by_scientific_name(self, search_term: str) -> List[tuple]:
        """Search for plants by scientific name (partial match)."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, scientific_name, family, genus, url
                FROM flora_plants
                WHERE scientific_name LIKE ?
                ORDER BY scientific_name
            """, (f'%{search_term}%',))

            results = cursor.fetchall()
            conn.close()

            return results
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return []

    def get_scientific_name_by_title(self, title: str) -> Optional[str]:
        """Get scientific name for a specific plant by its title."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT scientific_name
                FROM flora_plants
                WHERE title = ?
            """, (title,))

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else None
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return None

    def get_full_plant_info(self, scientific_name: str) -> Optional[Dict]:
        """Get complete information for a plant by scientific name."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM flora_plants
                WHERE scientific_name = ?
            """, (scientific_name,))

            result = cursor.fetchone()

            if result:
                columns = [description[0] for description in cursor.description]
                plant_info = dict(zip(columns, result))
                conn.close()
                return plant_info

            conn.close()
            return None
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return None

    def export_scientific_names_to_csv(self, filename: str = "scientific_names.csv"):
        """Export all scientific names to a CSV file."""
        try:
            conn = sqlite3.connect(self.db_name)

            df = pd.read_sql_query("""
                SELECT id, title, scientific_name, family, genus, species, complete
                FROM flora_plants
                WHERE scientific_name IS NOT NULL
                ORDER BY scientific_name
            """, conn)

            conn.close()

            df.to_csv(filename, index=False)
            logger.info(f"Exported {len(df)} scientific names to '{filename}'")
            print(f"Exported {len(df)} scientific names to '{filename}'")
            return df
        except Exception as e:
            logger.error(f"Export error: {e}")
            return None

    def get_scientific_names_by_family(self, family: str) -> List[tuple]:
        """Get all scientific names from a specific plant family."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT title, scientific_name, genus, species
                FROM flora_plants
                WHERE family = ? AND scientific_name IS NOT NULL
                ORDER BY scientific_name
            """, (family,))

            results = cursor.fetchall()
            conn.close()

            return results
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return []

    def get_statistics(self):
        """Print database statistics."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM flora_plants")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flora_plants WHERE complete = 1")
            complete = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flora_plants WHERE complete = 0")
            incomplete = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flora_plants WHERE scientific_name IS NOT NULL")
            with_sci_name = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM flora_plants WHERE scientific_name IS NULL")
            without_sci_name = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT family) FROM flora_plants WHERE family IS NOT NULL")
            families = cursor.fetchone()[0]

            conn.close()

            stats = {
                "total_entries": total,
                "complete_entries": complete,
                "incomplete_entries": incomplete,
                "with_scientific_name": with_sci_name,
                "without_scientific_name": without_sci_name,
                "unique_families": families
            }

            print(f"\nDatabase Statistics:")
            print(f"  Total entries: {stats['total_entries']}")
            print(f"  Complete entries: {stats['complete_entries']}")
            print(f"  Incomplete entries: {stats['incomplete_entries']}")
            print(f"  With scientific name: {stats['with_scientific_name']}")
            print(f"  Without scientific name: {stats['without_scientific_name']}")
            print(f"  Unique families: {stats['unique_families']}")
            
            return stats
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            print(f"\n⚠️  Database not accessible: {e}")
            print(f"   Database path: {self.db_name}")
            return {
                "total_entries": 0,
                "complete_entries": 0,
                "incomplete_entries": 0,
                "with_scientific_name": 0,
                "without_scientific_name": 0,
                "unique_families": 0
            }

    def mark_plant_complete(self, scientific_name: str, complete: bool = True) -> bool:
        """Mark a plant as complete or incomplete by scientific name.
        
        Args:
            scientific_name: The scientific name of the plant to update
            complete: True to mark as complete (1), False to mark as incomplete (0)
            
        Returns:
            True if update was successful, False if plant not found
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE flora_plants
                SET complete = ?
                WHERE scientific_name = ?
            """, (1 if complete else 0, scientific_name))

            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()

            if rows_affected > 0:
                status = "complete" if complete else "incomplete"
                logger.info(f"Marked '{scientific_name}' as {status}")
                print(f"✓ Marked '{scientific_name}' as {status}")
                return True
            else:
                logger.warning(f"Plant '{scientific_name}' not found")
                print(f"✗ Plant '{scientific_name}' not found")
                return False
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
            return False

    def print_scientific_names(self, limit: Optional[int] = None):
        """Print scientific names in a formatted way."""
        results = self.get_all_scientific_names()

        if limit:
            results = results[:limit]

        print(f"\n{'='*80}")
        print(f"Scientific Names (showing {len(results)} entries)")
        print(f"{'='*80}\n")

        for id, title, sci_name, url in results:
            print(f"ID: {id}")
            print(f"  Title: {title}")
            print(f"  Scientific Name: {sci_name}")
            print(f"  URL: {url}")
            print()

    def create_default_schema(self):
        """Create default database schema if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_name)
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

            conn.commit()
            conn.close()
            logger.info("Database schema created successfully")
            print("✓ Database schema created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            print(f"❌ Error creating schema: {e}")
            return False


# Example usage
if __name__ == "__main__":
    config = ConfigManager(verbose=True)
    config.print_summary()
    
    db = FloraDatabase(config)

    print("\n" + "=" * 80)
    print("EXAMPLE 1: Get all scientific names")
    print("=" * 80)
    all_names = db.get_all_scientific_names()
    print(f"Found {len(all_names)} plants with scientific names\n")

    for i, (id, title, sci_name, url) in enumerate(all_names[:5], 1):
        print(f"{i}. {title}: {sci_name}")

    print("\n" + "=" * 80)
    print("EXAMPLE 2: Get all incomplete plants")
    print("=" * 80)
    incomplete_plants = db.get_all_incomplete_plants()
    print(f"Found {len(incomplete_plants)} incomplete entries\n")

    for i, (id, title, sci_name, family, genus, url) in enumerate(incomplete_plants[:5], 1):
        print(f"{i}. {title}: {sci_name}")

    print("\n" + "=" * 80)
    print("EXAMPLE 3: Database statistics")
    print("=" * 80)
    db.get_statistics()

    print("\n" + "=" * 80)
    print("EXAMPLE 4: Print formatted list (first 3)")
    print("=" * 80)
    db.print_scientific_names(limit=3)