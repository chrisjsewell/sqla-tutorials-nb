(sqlatutorial:core-update-delete)=

# Updating and Deleting Rows with Core

So far we've covered {class}`~sqlalchemy.sql.expression.Insert`, so that we can get some data into
our database, and then spent a lot of time on {class}`~sqlalchemy.sql.expression.Select` which
handles the broad range of usage patterns used for retrieving data from the
database.   In this section we will cover the {class}`~sqlalchemy.sql.expression.Update` and
{class}`~sqlalchemy.sql.expression.Delete` constructs, which are used to modify existing rows
as well as delete existing rows.    This section will cover these constructs
from a Core-centric perspective.

:::{div} orm-header

**ORM Readers** - As was the case mentioned at {ref}`sqlatutorial:core-insert`,
the {class}`~sqlalchemy.sql.expression.Update` and {class}`~sqlalchemy.sql.expression.Delete` operations when used with
the ORM are usually invoked internally from the {class}`~sqlalchemy.orm.Session`
object as part of the {term}`unit of work` process.

However, unlike {class}`~sqlalchemy.sql.expression.Insert`, the {class}`~sqlalchemy.sql.expression.Update` and
{class}`~sqlalchemy.sql.expression.Delete` constructs can also be used directly with the ORM,
using a pattern known as "ORM-enabled update and delete"; for this reason,
familiarity with these constructs is useful for ORM use.  Both styles of
use are discussed in the sections {ref}`sqlatutorial:orm-updating` and
{ref}`sqlatutorial:orm-deleting`.
:::

(sqlatutorial:core-update)=

## The update() SQL Expression Construct

The {func}`~sqlalchemy.sql.expression.update` function generates a new instance of
{class}`~sqlalchemy.sql.expression.Update` which represents an UPDATE statement in SQL, that will
update existing data in a table.

Like the {func}`~sqlalchemy.sql.expression.insert` construct, there is a "traditional" form of
{func}`~sqlalchemy.sql.expression.update`, which emits UPDATE against a single table at a time and
does not return any rows.   However some backends support an UPDATE statement
that may modify multiple tables at once, and the UPDATE statement also
supports RETURNING such that columns contained in matched rows may be returned
in the result set.

A basic UPDATE looks like:

```
>>> from sqlalchemy import update
>>> stmt = (
...     update(user_table).where(user_table.c.name == 'patrick').
...     values(fullname='Patrick the Star')
... )
>>> print(stmt)
{opensql}UPDATE user_account SET fullname=:fullname WHERE user_account.name = :name_1
```

The {meth}`~sqlalchemy.sql.expression.Update.values` method controls the contents of the SET elements
of the UPDATE statement.  This is the same method shared by the {class}`~sqlalchemy.sql.expression.Insert`
construct.   Parameters can normally be passed using the column names as
keyword arguments.

UPDATE supports all the major SQL forms of UPDATE, including updates against expressions,
where we can make use of {class}`~sqlalchemy.schema.Column` expressions:

```
>>> stmt = (
...     update(user_table).
...     values(fullname="Username: " + user_table.c.name)
... )
>>> print(stmt)
{opensql}UPDATE user_account SET fullname=(:name_1 || user_account.name)
```

To support UPDATE in an "executemany" context, where many parameter sets will
be invoked against the same statement, the {func}`~sqlalchemy.sql.expression.bindparam`
construct may be used to set up bound parameters; these replace the places
that literal values would normally go:

```python
>>> from sqlalchemy import bindparam
>>> stmt = (
...   update(user_table).
...   where(user_table.c.name == bindparam('oldname')).
...   values(name=bindparam('newname'))
... )
>>> with engine.begin() as conn:
...   conn.execute(
...       stmt,
...       [
...          {'oldname':'jack', 'newname':'ed'},
...          {'oldname':'wendy', 'newname':'mary'},
...          {'oldname':'jim', 'newname':'jake'},
...       ]
...   )
{opensql}BEGIN (implicit)
UPDATE user_account SET name=? WHERE user_account.name = ?
[...] (('ed', 'jack'), ('mary', 'wendy'), ('jake', 'jim'))
<sqlalchemy.engine.cursor.CursorResult object at 0x...>
COMMIT{stop}
```

Other techniques which may be applied to UPDATE include:

(sqlatutorial:correlated-updates)=

### Correlated Updates

An UPDATE statement can make use of rows in other tables by using a
{ref}`correlated subquery <sqlatutorial:scalar-subquery>`.  A subquery may be used
anywhere a column expression might be placed:

```
>>> scalar_subq = (
...   select(address_table.c.email_address).
...   where(address_table.c.user_id == user_table.c.id).
...   order_by(address_table.c.id).
...   limit(1).
...   scalar_subquery()
... )
>>> update_stmt = update(user_table).values(fullname=scalar_subq)
>>> print(update_stmt)
{opensql}UPDATE user_account SET fullname=(SELECT address.email_address
FROM address
WHERE address.user_id = user_account.id ORDER BY address.id
LIMIT :param_1)
```

(sqlatutorial:update-from)=

### UPDATE..FROM

Some databases such as PostgreSQL and MySQL support a syntax "UPDATE FROM"
where additional tables may be stated directly in a special FROM clause. This
syntax will be generated implicitly when additional tables are located in the
WHERE clause of the statement:

```
>>> update_stmt = (
...    update(user_table).
...    where(user_table.c.id == address_table.c.user_id).
...    where(address_table.c.email_address == 'patrick@aol.com').
...    values(fullname='Pat')
...  )
>>> print(update_stmt)
{opensql}UPDATE user_account SET fullname=:fullname FROM address
WHERE user_account.id = address.user_id AND address.email_address = :email_address_1
```

There is also a MySQL specific syntax that can UPDATE multiple tables. This
requires we refer to {class}`~sqlalchemy.schema.Table` objects in the VALUES clause in
order to refer to additional tables:

```
>>> update_stmt = (
...    update(user_table).
...    where(user_table.c.id == address_table.c.user_id).
...    where(address_table.c.email_address == 'patrick@aol.com').
...    values(
...        {
...            user_table.c.fullname: "Pat",
...            address_table.c.email_address: "pat@aol.com"
...        }
...    )
...  )
>>> from sqlalchemy.dialects import mysql
>>> print(update_stmt.compile(dialect=mysql.dialect()))
{opensql}UPDATE user_account, address
SET address.email_address=%s, user_account.fullname=%s
WHERE user_account.id = address.user_id AND address.email_address = %s
```

### Parameter Ordered Updates

Another MySQL-only behavior is that the order of parameters in the SET clause
of an UPDATE actually impacts the evaluation of each expression.   For this use
case, the {meth}`~sqlalchemy.sql.expression.Update.ordered_values` method accepts a sequence of
tuples so that this order may be controlled [^id2]:

```
>>> update_stmt = (
...     update(some_table).
...     ordered_values(
...         (some_table.c.y, 20),
...         (some_table.c.x, some_table.c.y + 10)
...     )
... )
>>> print(update_stmt)
{opensql}UPDATE some_table SET y=:y, x=(some_table.y + :y_1)
```

[^id2]: While Python dictionaries are
    [guaranteed to be insert ordered](https://mail.python.org/pipermail/python-dev/2017-December/151283.html)
    as of Python 3.7, the
    {meth}`~sqlalchemy.sql.expression.Update.ordered_values` method still provides an additional
    measure of clarity of intent when it is essential that the SET clause
    of a MySQL UPDATE statement proceed in a specific way.

(sqlatutorial:deletes)=

## The delete() SQL Expression Construct

The {func}`~sqlalchemy.sql.expression.delete` function generates a new instance of
{class}`~sqlalchemy.sql.expression.Delete` which represents a DELETE statement in SQL, that will
delete rows from a table.

The {func}`~sqlalchemy.sql.expression.delete` statement from an API perspective is very similar to
that of the {func}`~sqlalchemy.sql.expression.update` construct, traditionally returning no rows but
allowing for a RETURNING variant on some database backends.

```
>>> from sqlalchemy import delete
>>> stmt = delete(user_table).where(user_table.c.name == 'patrick')
>>> print(stmt)
{opensql}DELETE FROM user_account WHERE user_account.name = :name_1
```

(sqlatutorial:multi-table-deletes)=

### Multiple Table Deletes

Like {class}`~sqlalchemy.sql.expression.Update`, {class}`~sqlalchemy.sql.expression.Delete` supports the use of correlated
subqueries in the WHERE clause as well as backend-specific multiple table
syntaxes, such as `DELETE FROM..USING` on MySQL:

```
>>> delete_stmt = (
...    delete(user_table).
...    where(user_table.c.id == address_table.c.user_id).
...    where(address_table.c.email_address == 'patrick@aol.com')
...  )
>>> from sqlalchemy.dialects import mysql
>>> print(delete_stmt.compile(dialect=mysql.dialect()))
{opensql}DELETE FROM user_account USING user_account, address
WHERE user_account.id = address.user_id AND address.email_address = %s
```

(sqlatutorial:update-delete-rowcount)=

## Getting Affected Row Count from UPDATE, DELETE

Both {class}`~sqlalchemy.sql.expression.Update` and {class}`~sqlalchemy.sql.expression.Delete` support the ability to
return the number of rows matched after the statement proceeds, for statements
that are invoked using Core {class}`~sqlalchemy.engine.Connection`, i.e.
{meth}`~sqlalchemy.engine.Connection.execute`. Per the caveats mentioned below, this value
is available from the {attr}`~sqlalchemy.engine.CursorResult.rowcount` attribute:

```python
>>> with engine.begin() as conn:
...     result = conn.execute(
...         update(user_table).
...         values(fullname="Patrick McStar").
...         where(user_table.c.name == 'patrick')
...     )
...     print(result.rowcount)
{opensql}BEGIN (implicit)
UPDATE user_account SET fullname=? WHERE user_account.name = ?
[...] ('Patrick McStar', 'patrick'){stop}
1
{opensql}COMMIT{stop}
```

:::{tip}
The {class}`~sqlalchemy.engine.CursorResult` class is a subclass of
{class}`~sqlalchemy.engine.Result` which contains additional attributes that are
specific to the DBAPI `cursor` object.  An instance of this subclass is
returned when a statement is invoked via the
{meth}`~sqlalchemy.engine.Connection.execute` method. When using the ORM, the
{meth}`~sqlalchemy.orm.Session.execute` method returns an object of this type for
all INSERT, UPDATE, and DELETE statements.
:::

Facts about {attr}`~sqlalchemy.engine.CursorResult.rowcount`:

- The value returned is the number of rows **matched** by the WHERE clause of
  the statement.   It does not matter if the row were actually modified or not.
- {attr}`~sqlalchemy.engine.CursorResult.rowcount` is not necessarily available for an UPDATE
  or DELETE statement that uses RETURNING.
- For an {ref}`executemany <sqlatutorial:multiple-parameters>` execution,
  {attr}`~sqlalchemy.engine.CursorResult.rowcount` may not be available either, which depends
  highly on the DBAPI module in use as well as configured options.  The
  attribute {attr}`~sqlalchemy.engine.CursorResult.supports_sane_multi_rowcount` indicates
  if this value will be available for the current backend in use.
- Some drivers, particularly third party dialects for non-relational databases,
  may not support {attr}`~sqlalchemy.engine.CursorResult.rowcount` at all.   The
  {attr}`~sqlalchemy.engine.CursorResult.supports_sane_rowcount` will indicate this.
- "rowcount" is used by the ORM {term}`unit of work` process to validate that
  an UPDATE or DELETE statement matched the expected number of rows, and is
  also essential for the ORM versioning feature documented at
  {ref}`mapper_version_counter`.

## Using RETURNING with UPDATE, DELETE

Like the {class}`~sqlalchemy.sql.expression.Insert` construct, {class}`~sqlalchemy.sql.expression.Update` and {class}`~sqlalchemy.sql.expression.Delete`
also support the RETURNING clause which is added by using the
{meth}`~sqlalchemy.sql.expression.Update.returning` and {meth}`~sqlalchemy.sql.expression.Delete.returning` methods.
When these methods are used on a backend that supports RETURNING, selected
columns from all rows that match the WHERE criteria of the statement
will be returned in the {class}`~sqlalchemy.engine.Result` object as rows that can
be iterated:

```
>>> update_stmt = (
...     update(user_table).where(user_table.c.name == 'patrick').
...     values(fullname='Patrick the Star').
...     returning(user_table.c.id, user_table.c.name)
... )
>>> print(update_stmt)
{opensql}UPDATE user_account SET fullname=:fullname
WHERE user_account.name = :name_1
RETURNING user_account.id, user_account.name{stop}

>>> delete_stmt = (
...     delete(user_table).where(user_table.c.name == 'patrick').
...     returning(user_table.c.id, user_table.c.name)
... )
>>> print(delete_stmt)
{opensql}DELETE FROM user_account
WHERE user_account.name = :name_1
RETURNING user_account.id, user_account.name{stop}
```

## Further Reading for UPDATE, DELETE

:::{seealso}
API documentation for UPDATE / DELETE:

- {class}`~sqlalchemy.sql.expression.Update`
- {class}`~sqlalchemy.sql.expression.Delete`

ORM-enabled UPDATE and DELETE:

- {ref}`sqlatutorial:orm-enabled-update`
- {ref}`sqlatutorial:orm-enabled-delete`
:::
