# SQLAlchemy Tutorial

The SQLAlchemy tutorial, using notebooks!

This content is adapted from <https://github.com/sqlalchemy/sqlalchemy/tree/master/doc/build/tutorial>, using sqlalchemy v1.4.22 (SHA: 044d951ea46cfa405ad9cae4319d6d44afda527a)

- Convert RST to MyST with [rst-to-myst](https://github.com/executablebooks/rst-to-myst)
  - `rst2myst convert -R doc/build/tutorial/*`
- Remove content above top-header in each file
- Replace inter-sphinx references


## TODO

- targets uses `-` but refs used `_` and myst-parser didn't like this.
- `rst-class` in `eval-rst` causes failure, unhandled pending node.
- Merge stdout/stder
- Better code hiding (title dropdown)
- Download as notebook for markdown file
