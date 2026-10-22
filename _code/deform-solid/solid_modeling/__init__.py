"""Newton-based sections of the project's validated deformed analytic solid."""
from .geometry import AnalyticCSG
from .deformation import Deformation
from .sections import Plane, Section, SectionOptions, cross_section, SectionError

__all__ = ['AnalyticCSG', 'Deformation', 'Plane', 'Section', 'SectionOptions',
           'cross_section', 'SectionError']
