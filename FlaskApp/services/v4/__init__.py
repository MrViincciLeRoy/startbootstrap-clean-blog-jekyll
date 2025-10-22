"""Research V4 package initialization"""

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