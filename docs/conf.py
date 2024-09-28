"""Configuration file for the Sphinx documentation builder."""
# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

from setuptools_scm import get_version  # type: ignore

sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

print(f"Building docs version: v{get_version(root='..')}")

project = f"Turn your oscilloscope into a lock in amplifier with this one simple trick! v{get_version(root='..')}"
author = "Marcus Engineering, LLC"
copyright = f"2024, {author}"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.autodoc", "sphinx.ext.intersphinx"]

# autodoc options
autodoc_member_order = "bysource"
autodoc_default_options = {
	"member-order": "bysource",
	# "undoc-members": True,
	"exclude-members": "__weakref__",
	# "special-members": "__init__, __new__",
}

maximum_signature_line_length = 80

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# -- Options for Latex output -------------------------------------------------

latex_logo = "_static/MENGR-Logo.png"

latex_elements = {
	"sphinxsetup": (
		"InnerLinkColor={rgb}{0,0.374,1.000}, OuterLinkColor={rgb}{0,0.374,1.000}"
	),
	"extraclassoptions": "openany,oneside",
	"preamble": r"""
\makeatletter
   \fancypagestyle{normal}{
% this is the stuff in sphinx.sty
    \fancyhf{}
    \fancyfoot[LE,RO]{{\py@HeaderFamily\thepage}}
% we comment this out and
    %\fancyfoot[LO]{{\py@HeaderFamily\nouppercase{\rightmark}}}
    %\fancyfoot[RE]{{\py@HeaderFamily\nouppercase{\leftmark}}}
% add copyright stuff
    \fancyfoot[LO,RE]{{\textcopyright\ """
	+ copyright
	+ " v"
	+ get_version(root="..")
	+ r"""}}
% again original stuff
    \fancyhead[LE,RO]{{\py@HeaderFamily \@title\sphinxheadercomma\py@release}}
    \renewcommand{\headrulewidth}{0.4pt}
    \renewcommand{\footrulewidth}{0.4pt}
    }
% this is applied to each opening page of a chapter
   \fancypagestyle{plain}{
    \fancyhf{}
    \fancyfoot[LE,RO]{{\py@HeaderFamily\thepage}}
    \renewcommand{\headrulewidth}{0pt}
    \renewcommand{\footrulewidth}{0.4pt}
% add copyright stuff for example at left of footer on odd pages,
% which is the case for chapter opening page by default
    \fancyfoot[LO,RE]{{\textcopyright\ """
	+ copyright
	+ " v"
	+ get_version(root="..")
	+ r"""}}
    }
\makeatother
""",
	"printindex": r"""
\let\oldtwocolumn\twocolumn
\renewcommand{\twocolumn}[1][]{#1}
\printindex
\renewcommand{\twocolumn}[1][]{\oldtwocolumn}
""",
}

latex_documents = [
	(
		"index",
		f'o_scope_lock_in_amplifier.v{get_version(root="..")}.tex',
		"Turn your oscilloscope into a lock in amplifier with this one simple trick!",
		"Marcus Engineering, LLC",
		"manual",
	),
]
