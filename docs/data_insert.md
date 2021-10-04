---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
language_info:
  name: python
  codemirror_mode:
    name: ipython
    version: 3
---

(sqlatutorial:core-insert)=

# Inserting Rows with Core

When using Core, a SQL INSERT statement is generated using the {func}`~sqlalchemy.sql.expression.insert` function -
this function generates a new instance of {class}`~sqlalchemy.sql.expression.Insert` which represents an INSERT statement in SQL,
that adds new data into a table.

:::{div} orm-header

**ORM Readers** - The way that rows are INSERTed into the database from an ORM
perspective makes use of object-centric APIs on the {class}`~sqlalchemy.orm.Session` object known as the
{term}`unit of work` process,
and is fairly different from the Core-only approach described here.
The more ORM-focused sections later starting at {ref}`sqlatutorial:inserting-orm`
subsequent to the Expression Language sections introduce this.
:::

```{code-cell} ipython3
:tags: [hide-output]

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey

metadata = MetaData()
user_table = Table(
    "user_account",
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(30)),
    Column('fullname', String)
)
address_table = Table(
    "address",
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', ForeignKey('user_account.id'), nullable=False),
    Column('email_address', String, nullable=False)
)

engine = create_engine("sqlite+pysqlite:///:memory:", echo=True, future=True)
metadata.create_all(engine)
```

## The insert() SQL Expression Construct

A simple example of {class}`~sqlalchemy.sql.expression.Insert` illustrating the target table
and the VALUES clause at once:

```{code-cell} ipython3
from sqlalchemy import insert
stmt = insert(user_table).values(name='spongebob', fullname="Spongebob Squarepants")
```

The above `stmt` variable is an instance of {class}`~sqlalchemy.sql.expression.Insert`.  Most
SQL expressions can be stringified in place as a means to see the general
form of what's being produced:

```{code-cell} ipython3
print(stmt)
```

The stringified form is created by producing a {class}`~sqlalchemy.engine.Compiled` form
of the object which includes a database-specific string SQL representation of
the statement; we can acquire this object directly using the
{meth}`~sqlalchemy.sql.expression.ClauseElement.compile` method:

```{code-cell} ipython3
compiled = stmt.compile()
```

Our {class}`~sqlalchemy.sql.expression.Insert` construct is an example of a "parameterized"
construct, illustrated previously at {ref}`sqlatutorial:sending-parameters`; to
view the `name` and `fullname` {term}`bound parameters`, these are
available from the {class}`~sqlalchemy.engine.Compiled` construct as well:

```{code-cell} ipython3
compiled.params
```

## Executing the Statement

Invoking the statement we can INSERT a row into `user_table`.
The INSERT SQL as well as the bundled parameters can be seen in the
SQL logging:

```{code-cell} ipython3
with engine.connect() as conn:
    result = conn.execute(stmt)
    conn.commit()
```

In its simple form above, the INSERT statement does not return any rows, and if
only a single row is inserted, it will usually include the ability to return
information about column-level default values that were generated during the
INSERT of that row, most commonly an integer primary key value.  In the above
case the first row in a SQLite database will normally return `1` for the
first integer primary key value, which we can acquire using the
{attr}`~sqlalchemy.engine.CursorResult.inserted_primary_key` accessor:

```{code-cell} ipython3
result.inserted_primary_key
```

:::{tip}
{attr}`~sqlalchemy.engine.CursorResult.inserted_primary_key` returns a tuple
because a primary key may contain multiple columns.  This is known as
a {term}`composite primary key`.  The {attr}`~sqlalchemy.engine.CursorResult.inserted_primary_key`
is intended to always contain the complete primary key of the record just
inserted, not just a "cursor.lastrowid" kind of value, and is also intended
to be populated regardless of whether or not "autoincrement" were used, hence
to express a complete primary key it's a tuple.
:::

:::{versionchanged} 1.4.8 the tuple returned by :attr:`_engine.CursorResult.inserted_primary_key` is now a named tuple fullfilled by returning it as a :class:`_result.Row` object.
:::

(sqlatutorial:core-insert-values-clause)=

## INSERT usually generates the "values" clause automatically

The example above made use of the {meth}`~sqlalchemy.sql.expression.Insert.values` method to
explicitly create the VALUES clause of the SQL INSERT statement.   This method
in fact has some variants that allow for special forms such as multiple rows in
one statement and insertion of SQL expressions.   However the usual way that
{class}`~sqlalchemy.sql.expression.Insert` is used is such that the VALUES clause is generated
automatically from the parameters passed to the
{meth}`~sqlalchemy.future.Connection.execute` method; below we INSERT two more rows to
illustrate this:

```{code-cell} ipython3
with engine.connect() as conn:
    result = conn.execute(
        insert(user_table),
        [
            {"name": "sandy", "fullname": "Sandy Cheeks"},
            {"name": "patrick", "fullname": "Patrick Star"}
        ]
    )
    conn.commit()
```

The execution above features "executemany" form first illustrated at
{ref}`sqlatutorial:multiple-parameters`, however unlike when using the
{func}`~sqlalchemy.sql.expression.text` construct, we didn't have to spell out any SQL.
By passing a dictionary or list of dictionaries to the {meth}`~sqlalchemy.future.Connection.execute`
method in conjunction with the {class}`~sqlalchemy.sql.expression.Insert` construct, the
{class}`~sqlalchemy.future.Connection` ensures that the column names which are passed
will be expressed in the VALUES clause of the {class}`~sqlalchemy.sql.expression.Insert`
construct automatically.

:::{dropdown} Deep Alchemy
:color: info

Hi, welcome to the first edition of **Deep Alchemy**.   The person on the
left is known as **The Alchemist**, and you'll note they are **not** a wizard,
as the pointy hat is not sticking upwards.   The Alchemist comes around to
describe things that are generally **more advanced and/or tricky** and
additionally **not usually needed**, but for whatever reason they feel you
should know about this thing that SQLAlchemy can do.

In this edition, towards the goal of having some interesting data in the
`address_table` as well, below is a more advanced example illustrating
how the {meth}`~sqlalchemy.sql.expression.Insert.values` method may be used explicitly while at
the same time including for additional VALUES generated from the
parameters.
A {term}`scalar subquery` is constructed, making use of the
{func}`~sqlalchemy.sql.expression.select` construct introduced in the next section, and the
parameters used in the subquery are set up using an explicit bound
parameter name, established using the {func}`~sqlalchemy.sql.expression.bindparam` construct.

This is some slightly **deeper** alchemy just so that we can add related
rows without fetching the primary key identifiers from the ``user_table``
operation into the application.
Most Alchemists will simply use the ORM
which takes care of things like this for us.

```python
from sqlalchemy import select, bindparam
scalar_subquery = (
    select(user_table.c.id).
    where(user_table.c.name==bindparam('username')).
    scalar_subquery()
)

with engine.connect() as conn:
    result = conn.execute(
        insert(address_table).values(user_id=scalar_subquery),
        [
            {"username": 'spongebob', "email_address": "spongebob@sqlalchemy.org"},
            {"username": 'sandy', "email_address": "sandy@sqlalchemy.org"},
            {"username": 'sandy', "email_address": "sandy@squirrelpower.org"},
        ]
    )
    conn.commit()
```

```
{opensql}BEGIN (implicit)
INSERT INTO address (user_id, email_address) VALUES ((SELECT user_account.id
FROM user_account
WHERE user_account.name = ?), ?)
[...] (('spongebob', 'spongebob@sqlalchemy.org'), ('sandy', 'sandy@sqlalchemy.org'),
('sandy', 'sandy@squirrelpower.org'))
COMMIT{stop}
```

:::

(sqlatutorial:insert-from-select)=

## INSERT...FROM SELECT

The {class}`~sqlalchemy.sql.expression.Insert` construct can compose
an INSERT that gets rows directly from a SELECT using the {meth}`~sqlalchemy.sql.expression.Insert.from_select`
method:

```{code-cell} ipython3
from sqlalchemy import select

select_stmt = select(user_table.c.id, user_table.c.name + "@aol.com")
insert_stmt = insert(address_table).from_select(
    ["user_id", "email_address"], select_stmt
)
print(insert_stmt)
```

(sqlatutorial:insert-returning)=

## INSERT...RETURNING

The RETURNING clause for supported backends is used
automatically in order to retrieve the last inserted primary key value
as well as the values for server defaults.   However the RETURNING clause
may also be specified explicitly using the {meth}`~sqlalchemy.sql.expression.Insert.returning`
method; in this case, the {class}`~sqlalchemy.engine.Result`
object that's returned when the statement is executed has rows which
can be fetched:

```{code-cell} ipython3
insert_stmt = insert(address_table).returning(address_table.c.id, address_table.c.email_address)
print(insert_stmt)
```

It can also be combined with {meth}`~sqlalchemy.sql.expression.Insert.from_select`,
as in the example below that builds upon the example stated in
{ref}`sqlatutorial:insert-from-select`:

```{code-cell} ipython3
select_stmt = select(user_table.c.id, user_table.c.name + "@aol.com")
insert_stmt = insert(address_table).from_select(
    ["user_id", "email_address"], select_stmt
)
print(insert_stmt.returning(address_table.c.id, address_table.c.email_address))
```

:::{tip}
The RETURNING feature is also supported by UPDATE and DELETE statements,
which will be introduced later in this tutorial.
The RETURNING feature is generally [^id2] only
supported for statement executions that use a single set of bound
parameters; that is, it wont work with the "executemany" form introduced
at {ref}`sqlatutorial:multiple-parameters`.    Additionally, some dialects
such as the Oracle dialect only allow RETURNING to return a single row
overall, meaning it won't work with "INSERT..FROM SELECT" nor will it
work with multiple row {class}`~sqlalchemy.sql.expression.Update` or {class}`~sqlalchemy.sql.expression.Delete`
forms.

[^id2]: There is internal support for the
    {mod}`~sqlalchemy.dialects.postgresql.psycopg2` dialect to INSERT many rows at once
    and also support RETURNING, which is leveraged by the SQLAlchemy
    ORM.   However this feature has not been generalized to all dialects
    and is not yet part of SQLAlchemy's regular API.
:::

:::{seealso}
{class}`~sqlalchemy.sql.expression.Insert` - in the SQL Expression API documentation
:::
