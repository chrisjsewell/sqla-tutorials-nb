"""Sphinx configuration"""
project = "SQLAlchemy Tutorial"

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", '**.ipynb_checkpoints']

extensions = ["myst_nb", "sphinx.ext.intersphinx", "sphinx_copybutton", "sphinx_design"]

myst_enable_extensions = ["colon_fence"]

intersphinx_mapping = {
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/14/", None),
}
# note, find things in the inventory with:
# sphobjinv suggest --url "https://docs.sqlalchemy.org/en/14/objects.inv" Engine

html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]


def setup(app):
    """Setup the Sphinx app"""
    from typing import cast
    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.util.docutils import SphinxRole

    app = cast(Sphinx, app)

    class ParamRef(SphinxRole):
        """Dummy role for https://pypi.org/project/sphinx-paramlinks/, which is not currently compatible with sphinx v4."""

        def run(self):
            node = nodes.literal(self.text, self.text.split(".")[-1])
            return ([node], [])

    app.add_role("paramref", ParamRef())
