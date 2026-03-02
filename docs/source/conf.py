import os
import sys

# -- Path setup --------------------------------------------------------------
# This points Sphinx to your root directory where main.py and the game folder live
sys.path.insert(0, os.path.abspath("../../"))

# -- Project information -----------------------------------------------------
project = "Power City Builder"
copyright = "2026, black-hole-diver"
author = "black-hole-diver"
release = "v1.0.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",  # Core: Pulls in docstrings from your code
    "sphinx.ext.napoleon",  # Support for Google/NumPy style docstrings
    "sphinx.ext.viewcode",  # Adds " [source] " links next to your classes/methods
    "sphinx.ext.githubpages",  # Optimized for hosting on GitHub Pages
]

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# Swapping 'alabaster' for the industry-standard blue/white theme
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
