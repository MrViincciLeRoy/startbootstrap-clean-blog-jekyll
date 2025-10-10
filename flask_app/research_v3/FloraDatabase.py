
import sqlite3
import pandas as pd
from typing import List, Dict, Optional

class FloraDatabase:
    def __init__(self, db_name: str = "flora_data.db"):
        """Initialize database connection."""
        self.db_name = db_name

    def get_all_scientific_names(self) -> List[tuple]:
        """Get all scientific names from the database."""
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

    def get_scientific_names_with_complete_data(self) -> List[tuple]:
        """Get scientific names only for complete entries."""
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

    def check_if_complete(self, scientific_name: str) -> Optional[bool]:
        """Check if a plant with the given scientific name has complete data.

        Returns:
            True if complete = 1
            False if complete = 0
            None if scientific name not found
        """
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

    def get_all_incomplete_plants(self) -> List[tuple]:
        """Get all plants with complete = 0 (incomplete data).

        Returns:
            List of tuples: (id, title, scientific_name, family, genus, url)
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, scientific_name, family, genus, url
            FROM flora_plants
            WHERE complete = 1
            ORDER BY scientific_name
        """)

        results = cursor.fetchall()
        conn.close()

        return results

    def search_by_scientific_name(self, search_term: str) -> List[tuple]:
        """Search for plants by scientific name (partial match)."""
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

    def get_scientific_name_by_title(self, title: str) -> Optional[str]:
        """Get scientific name for a specific plant by its title."""
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

    def get_full_plant_info(self, scientific_name: str) -> Optional[Dict]:
        """Get complete information for a plant by scientific name."""
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

    def export_scientific_names_to_csv(self, filename: str = "scientific_names.csv"):
        """Export all scientific names to a CSV file."""
        conn = sqlite3.connect(self.db_name)

        df = pd.read_sql_query("""
            SELECT id, title, scientific_name, family, genus, species, complete
            FROM flora_plants
            WHERE scientific_name IS NOT NULL
            ORDER BY scientific_name
        """, conn)

        conn.close()

        df.to_csv(filename, index=False)
        print(f"Exported {len(df)} scientific names to '{filename}'")
        return df

    def get_scientific_names_by_family(self, family: str) -> List[tuple]:
        """Get all scientific names from a specific plant family."""
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

    def get_statistics(self):
        """Print database statistics."""
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

        print(f"\nDatabase Statistics:")
        print(f"  Total entries: {total}")
        print(f"  Complete entries: {complete}")
        print(f"  Incomplete entries: {incomplete}")
        print(f"  With scientific name: {with_sci_name}")
        print(f"  Without scientific name: {without_sci_name}")
        print(f"  Unique families: {families}")

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


# Example usage demonstrations
if __name__ == "__main__":
    db = FloraDatabase("flora_data.db")

    # Example 1: Get all scientific names
    print("=" * 80)
    print("EXAMPLE 1: Get all scientific names")
    print("=" * 80)
    all_names = db.get_all_scientific_names()
    print(f"Found {len(all_names)} plants with scientific names\n")

    # Show first 5
    for i, (id, title, sci_name, url) in enumerate(all_names[:5], 1):
        print(f"{i}. {title}: {sci_name}")

    # Example 2: Get only complete entries
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Get complete entries only")
    print("=" * 80)
    complete_names = db.get_scientific_names_with_complete_data()
    print(f"Found {len(complete_names)} complete entries\n")

    for i, (id, title, sci_name, family, genus, url) in enumerate(complete_names[:5], 1):
        print(f"{i}. {title}: {sci_name} (Family: {family})")

    # Example 3: Check if a scientific name is complete
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Check if scientific name has complete data")
    print("=" * 80)
    if all_names:
        test_sci_name = all_names[0][2]
        is_complete = db.check_if_complete(test_sci_name)
        if is_complete is not None:
            status = "Complete" if is_complete else "Incomplete"
            print(f"'{test_sci_name}' is: {status}")
        else:
            print(f"'{test_sci_name}' not found in database")

    # Example 4: Get all incomplete plants
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Get all incomplete plants")
    print("=" * 80)
    incomplete_plants = db.get_all_incomplete_plants()
    print(f"Found {len(incomplete_plants)} incomplete entries\n")

    for i, (id, title, sci_name, family, genus, url) in enumerate(incomplete_plants[:5], 1):
        print(f"{i}. {title}: {sci_name}")

    # Example 5: Search by partial name
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Search for plants with 'Adeno' in scientific name")
    print("=" * 80)
    search_results = db.search_by_scientific_name("Adeno")
    for id, title, sci_name, family, genus, url in search_results[:5]:
        print(f"  {title}: {sci_name}")

    # Example 6: Get scientific name by title
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Get scientific name by plant title")
    print("=" * 80)
    sci_name = db.get_scientific_name_by_title("Adenocline")
    if sci_name:
        print(f"Scientific name for 'Adenocline': {sci_name}")
    else:
        print("Plant not found")

    # Example 7: Get full plant information
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Get full information by scientific name")
    print("=" * 80)
    if all_names:
        first_sci_name = all_names[0][2]
        plant_info = db.get_full_plant_info(first_sci_name)
        if plant_info:
            print(f"\nFull information for {first_sci_name}:")
            for key, value in plant_info.items():
                if value and key not in ['raw_data']:
                    print(f"  {key}: {value}")

    # Example 8: Export to CSV
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Export scientific names to CSV")
    print("=" * 80)
    try:
        df = db.export_scientific_names_to_csv("scientific_names.csv")
        print(f"\nFirst few rows:")
        print(df.head())
    except Exception as e:
        print(f"Could not export (pandas might not be installed): {e}")

    # Example 9: Get statistics
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Database statistics")
    print("=" * 80)
    db.get_statistics()

    # Example 10: Print formatted list
    print("\n" + "=" * 80)
    print("EXAMPLE 10: Print formatted list (first 3)")
    print("=" * 80)
    db.print_scientific_names(limit=3)