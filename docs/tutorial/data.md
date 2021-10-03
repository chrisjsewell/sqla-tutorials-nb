(sqlatutorial:working-with-data)=

# Working with Data

In {ref}`sqlatutorial:working-with-transactions`, we learned the basics of how to
interact with the Python DBAPI and its transactional state.  Then, in
{ref}`sqlatutorial:working-with-metadata`, we learned how to represent database
tables, columns, and constraints within SQLAlchemy using the
{class}`~sqlalchemy.schema.MetaData` and related objects.  In this section we will combine
both concepts above to create, select and manipulate data within a relational
database.   Our interaction with the database is **always** in terms
of a transaction, even if we've set our database driver to use {ref}`autocommit
<dbapi_autocommit>` behind the scenes.

The components of this section are as follows:

- {ref}`sqlatutorial:core-insert` - to get some data into the database, we introduce
  and demonstrate the Core {class}`~sqlalchemy.sql.expression.Insert` construct.   INSERTs from an
  ORM perspective are described in the next section
  {ref}`sqlatutorial:orm-data-manipulation`.
- {ref}`sqlatutorial:selecting-data` - this section will describe in detail
  the {class}`~sqlalchemy.sql.expression.Select` construct, which is the most commonly used object
  in SQLAlchemy.  The {class}`~sqlalchemy.sql.expression.Select` construct emits SELECT statements
  for both Core and ORM centric applications and both use cases will be
  described here.   Additional ORM use cases are also noted in the later
  section {ref}`sqlatutorial:select-relationships` as well as the
  {ref}`queryguide_toplevel`.
- {ref}`sqlatutorial:core-update-delete` - Rounding out the INSERT and SELECTion
  of data, this section will describe from a Core perspective the use of the
  {class}`~sqlalchemy.sql.expression.Update` and {class}`~sqlalchemy.sql.expression.Delete` constructs.  ORM-specific
  UPDATE and DELETE is similarly described in the
  {ref}`sqlatutorial:orm-data-manipulation` section.

```{toctree}
:hidden: true
:maxdepth: 10

data_insert
data_select
data_update
```
