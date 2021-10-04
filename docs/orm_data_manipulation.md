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
  mimetype: text/x-python
  codemirror_mode:
    name: ipython
    version: 3
---

(sqlatutorial:orm-data-manipulation)=

# Data Manipulation with the ORM

The previous section {ref}`sqlatutorial:working-with-data` remained focused on
the SQL Expression Language from a Core perspective, in order to provide
continuity across the major SQL statement constructs.  This section will
then build out the lifecycle of the {class}`~sqlalchemy.orm.Session` and how it interacts
with these constructs.

**Prerequisite Sections** - the ORM focused part of the tutorial builds upon
two previous ORM-centric sections in this document:

- {ref}`sqlatutorial:executing-orm-session` - introduces how to make an ORM {class}`~sqlalchemy.orm.Session` object
- {ref}`sqlatutorial:orm-table-metadata` - where we set up our ORM mappings of the `User` and `Address` entities
- {ref}`sqlatutorial:selecting-orm-entities` - a few examples on how to run SELECT statements for entities like `User`

```{code-cell} ipython3
:tags: [hide-output]

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey, select, insert, update, delete
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()

class User(Base):
    __tablename__ = 'user_account'

    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    fullname = Column(String)

    def __repr__(self):
        return f"User({self.name!r}, {self.fullname!r})"

class Address(Base):
    __tablename__ = 'address'

    id = Column(Integer, primary_key=True)
    email_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('user_account.id'))

    def __repr__(self):
        return f"Address({self.email_address!r})"

engine = create_engine("sqlite+pysqlite:///:memory:", echo=True, future=True)
Base.metadata.create_all(engine)

with engine.begin() as conn:
    conn.execute(
        insert(User),
        [
            {"id": 1, "name": "spongebob", "fullname": "Spongebob Squarepants"},
            {"id": 2, "name": "sandy", "fullname": "Sandy Cheeks"},
            {"id": 3, "name": "patrick", "fullname": "Patrick Star"}
        ]
    )
with engine.begin() as conn:
    conn.execute(
        insert(Address),
        [
            {"user_id": 1, "email_address": "spongebob@sqlalchemy.org"},
            {"user_id": 2, "email_address": "sandy@sqlalchemy.org"},
            {"user_id": 2, "email_address": "sandy@squirrelpower.org"},
        ]
    )
```

(sqlatutorial:inserting-orm)=

## Inserting Rows with the ORM

When using the ORM, the {class}`~sqlalchemy.orm.Session` object is responsible for
constructing {class}`~sqlalchemy.sql.expression.Insert` constructs and emitting them for us in a
transaction. The way we instruct the {class}`~sqlalchemy.orm.Session` to do so is by
**adding** object entries to it; the {class}`~sqlalchemy.orm.Session` then makes sure
these new entries will be emitted to the database when they are needed, using
a process known as a **flush**.

### Instances of Classes represent Rows

Whereas in the previous example we emitted an INSERT using Python dictionaries
to indicate the data we wanted to add, with the ORM we make direct use of the
custom Python classes we defined, back at
{ref}`sqlatutorial:orm-table-metadata`.    At the class level, the `User` and
`Address` classes served as a place to define what the corresponding
database tables should look like.   These classes also serve as extensible
data objects that we use to create and manipulate rows within a transaction
as well.  Below we will create two `User` objects each representing a
potential database row to be INSERTed:

```{code-cell} ipython3
squidward = User(name="squidward", fullname="Squidward Tentacles")
krabs = User(name="ehkrabs", fullname="Eugene H. Krabs")
```

We are able to construct these objects using the names of the mapped columns as
keyword arguments in the constructor.  This is possible as the `User` class
includes an automatically generated `__init__()` constructor that was
provided by the ORM mapping so that we could create each object using column
names as keys in the constructor.

In a similar manner as in our Core examples of {class}`~sqlalchemy.sql.expression.Insert`, we did not
include a primary key (i.e. an entry for the `id` column), since we would
like to make use of the auto-incrementing primary key feature of the database,
SQLite in this case, which the ORM also integrates with.
The value of the `id` attribute on the above
objects, if we were to view it, displays itself as `None`:

```{code-cell} ipython3
squidward
```

The `None` value is provided by SQLAlchemy to indicate that the attribute
has no value as of yet.  SQLAlchemy-mapped attributes always return a value
in Python and don't raise `AttributeError` if they're missing, when
dealing with a new object that has not had a value assigned.

At the moment, our two objects above are said to be in a state called
{term}`transient` - they are not associated with any database state and are yet
to be associated with a {class}`~sqlalchemy.orm.Session` object that can generate
INSERT statements for them.

### Adding objects to a Session

To illustrate the addition process step by step, we will create a
{class}`~sqlalchemy.orm.Session` without using a context manager (and hence we must make sure we close it later!):

```{code-cell} ipython3
session = Session(engine)
```

The objects are then added to the {class}`~sqlalchemy.orm.Session` using the
{meth}`~sqlalchemy.orm.Session.add` method.   When this is called, the objects are in a
state known as {term}`pending` and have not been inserted yet:

```{code-cell} ipython3
session.add(squidward)
session.add(krabs)
```

When we have pending objects, we can see this state by looking at a
collection on the {class}`~sqlalchemy.orm.Session` called {attr}`~sqlalchemy.orm.Session.new`:

```{code-cell} ipython3
session.new
```

The above view is using a collection called {class}`~sqlalchemy.sql.schema.Identity` that is
essentially a Python set that hashes on object identity in all cases (i.e.,
using Python built-in `id()` function, rather than the Python `hash()` function).

### Flushing

The {class}`~sqlalchemy.orm.Session` makes use of a pattern known as {term}`unit of work`.
This generally means it accumulates changes one at a time, but does not actually
communicate them to the database until needed.   This allows it to make
better decisions about how SQL DML should be emitted in the transaction based
on a given set of pending changes.   When it does emit SQL to the database
to push out the current set of changes, the process is known as a **flush**.

We can illustrate the flush process manually by calling the {meth}`~sqlalchemy.orm.Session.flush`
method:

```{code-cell} ipython3
session.flush()
```

Above we observe the {class}`~sqlalchemy.orm.Session` was first called upon to emit SQL,
so it created a new transaction and emitted the appropriate INSERT statements
for the two objects.   The transaction now **remains open** until we call any
of the {meth}`~sqlalchemy.orm.Session.commit`, {meth}`~sqlalchemy.orm.Session.rollback`, or
{meth}`~sqlalchemy.orm.Session.close` methods of {class}`~sqlalchemy.orm.Session`.

While {meth}`~sqlalchemy.orm.Session.flush` may be used to manually push out pending
changes to the current transaction, it is usually unnecessary as the
{class}`~sqlalchemy.orm.Session` features a behavior known as **autoflush**, which
we will illustrate later.   It also flushes out changes whenever
{meth}`~sqlalchemy.orm.Session.commit` is called.

### Autogenerated primary key attributes

Once the rows are inserted, the two Python objects we've created are in a
state known as {term}`persistent`, where they are associated with the
{class}`~sqlalchemy.orm.Session` object in which they were added or loaded, and feature lots of
other behaviors that will be covered later.

Another effect of the INSERT that occurred was that the ORM has retrieved the
new primary key identifiers for each new object; internally it normally uses
the same {attr}`~sqlalchemy.engine.CursorResult.inserted_primary_key` accessor we
introduced previously.   The `squidward` and `krabs` objects now have these new
primary key identifiers associated with them and we can view them by acesssing
the `id` attribute:

```{code-cell} ipython3
squidward.id
```

```{code-cell} ipython3
krabs.id
```

:::{tip}
Why did the ORM emit two separate INSERT statements when it could have
used {ref}`executemany <sqlatutorial:multiple-parameters>`?  As we'll see in the
next section, the
{class}`~sqlalchemy.orm.Session` when flushing objects always needs to know the
primary key of newly inserted objects.  If a feature such as SQLite's autoincrement is used
(other examples include PostgreSQL IDENTITY or SERIAL, using sequences,
etc.), the {attr}`~sqlalchemy.engine.CursorResult.inserted_primary_key` feature
usually requires that each INSERT is emitted one row at a time.  If we had provided values for the primary keys ahead of
time, the ORM would have been able to optimize the operation better.  Some
database backends such as {ref}`psycopg2 <postgresql_psycopg2>` can also
INSERT many rows at once while still being able to retrieve the primary key
values.
:::

### Identity Map

The primary key identity of the objects are significant to the {class}`~sqlalchemy.orm.Session`,
as the objects are now linked to this identity in memory using a feature
known as the {term}`identity map`.   The identity map is an in-memory store
that links all objects currently loaded in memory to their primary key
identity.   We can observe this by retrieving one of the above objects
using the {meth}`~sqlalchemy.orm.Session.get` method, which will return an entry
from the identity map if locally present, otherwise emitting a SELECT:

```{code-cell} ipython3
some_squidward = session.get(User, 4)
some_squidward
```

The important thing to note about the identity map is that it maintains a
**unique instance** of a particular Python object per a particular database
identity, within the scope of a particular {class}`~sqlalchemy.orm.Session` object.  We
may observe that the `some_squidward` refers to the **same object** as that
of `squidward` previously:

```{code-cell} ipython3
some_squidward is squidward
```

The identity map is a critical feature that allows complex sets of objects
to be manipulated within a transaction without things getting out of sync.

### Committing

There's much more to say about how the {class}`~sqlalchemy.orm.Session` works which will
be discussed further.   For now we will commit the transaction so that
we can build up knowledge on how to SELECT rows before examining more ORM
behaviors and features:

```{code-cell} ipython3
session.commit()
```

(sqlatutorial:orm-updating)=

## Updating ORM Objects

In the preceding section {ref}`sqlatutorial:core-update-delete`, we introduced the
{class}`~sqlalchemy.sql.expression.Update` construct that represents a SQL UPDATE statement. When
using the ORM, there are two ways in which this construct is used. The primary
way is that it is emitted automatically as part of the {term}`unit of work`
process used by the {class}`~sqlalchemy.orm.Session`, where an UPDATE statement is emitted
on a per-primary key basis corresponding to individual objects that have
changes on them.   A second form of UPDATE is called an "ORM enabled
UPDATE" and allows us to use the {class}`~sqlalchemy.sql.expression.Update` construct with the
{class}`~sqlalchemy.orm.Session` explicitly; this is described in the next section.

Supposing we loaded the `User` object for the username `sandy` into
a transaction (also showing off the {meth}`~sqlalchemy.sql.expression.Select.filter_by` method
as well as the {meth}`~sqlalchemy.engine.Result.scalar_one` method):

```{code-cell} ipython3
sandy = session.execute(select(User).filter_by(name="sandy")).scalar_one()
```

The Python object `sandy` as mentioned before acts as a **proxy** for the
row in the database, more specifically the database row **in terms of the
current transaction**, that has the primary key identity of `2`:

```{code-cell} ipython3
sandy
```

If we alter the attributes of this object, the {class}`~sqlalchemy.orm.Session` tracks
this change:

```{code-cell} ipython3
sandy.fullname = "Sandy Squirrel"
```

The object appears in a collection called {attr}`~sqlalchemy.orm.Session.dirty`, indicating
the object is "dirty":

```{code-cell} ipython3
sandy in session.dirty
```

When the {class}`~sqlalchemy.orm.Session` next emits a flush, an UPDATE will be emitted
that updates this value in the database.  As mentioned previously, a flush
occurs automatically before we emit any SELECT, using a behavior known as
**autoflush**.  We can query directly for the `User.fullname` column
from this row and we will get our updated value back:

```{code-cell} ipython3
sandy_fullname = session.execute(
    select(User.fullname).where(User.id == 2)
).scalar_one()
print(sandy_fullname)
```

We can see above that we requested that the {class}`~sqlalchemy.orm.Session` execute
a single {func}`~sqlalchemy.sql.expression.select` statement.  However the SQL emitted shows
that an UPDATE were emitted as well, which was the flush process pushing
out pending changes.  The `sandy` Python object is now no longer considered
dirty:

```{code-cell} ipython3
sandy in session.dirty
```

However note we are **still in a transaction** and our changes have not
been pushed to the database's permanent storage.   Since Sandy's last name
is in fact "Cheeks" not "Squirrel", we will repair this mistake later when
we roll back the transction.  But first we'll make some more data changes.

:::{seealso}
{ref}`session_flushing`- details the flush process as well as information
about the {paramref}`~sqlalchemy.orm.Session.autoflush` setting.
:::

(sqlatutorial:orm-enabled-update)=

### ORM-enabled UPDATE statements

As previously mentioned, there's a second way to emit UPDATE statements in
terms of the ORM, which is known as an **ORM enabled UPDATE statement**.   This allows the use
of a generic SQL UPDATE statement that can affect many rows at once.   For example
to emit an UPDATE that will change the `User.fullname` column based on
a value in the `User.name` column:

```{code-cell} ipython3
session.execute(
    update(User).
    where(User.name == "sandy").
    values(fullname="Sandy Squirrel Extraordinaire")
)
```

When invoking the ORM-enabled UPDATE statement, special logic is used to locate
objects in the current session that match the given criteria, so that they
are refreshed with the new data.  Above, the `sandy` object identity
was located in memory and refreshed:

```{code-cell} ipython3
sandy.fullname
```

The refresh logic is known as the `synchronize_session` option, and is described
in detail in the section {ref}`orm_expression_update_delete`.

:::{seealso}
{ref}`orm_expression_update_delete` - describes ORM use of {func}`~sqlalchemy.sql.expression.update`
and {func}`~sqlalchemy.sql.expression.delete` as well as ORM synchronization options.
:::

(sqlatutorial:orm-deleting)=

## Deleting ORM Objects

To round out the basic persistence operations, an individual ORM object
may be marked for deletion by using the {meth}`~sqlalchemy.orm.Session.delete` method.
Let's load up `patrick` from the database:

```{code-cell} ipython3
patrick = session.get(User, 3)
```

If we mark `patrick` for deletion, as is the case with other operations,
nothing actually happens yet until a flush proceeds:

```{code-cell} ipython3
session.delete(patrick)
```

Current ORM behavior is that `patrick` stays in the {class}`~sqlalchemy.orm.Session`
until the flush proceeds, which as mentioned before occurs if we emit a query:

```{code-cell} ipython3
session.execute(select(User).where(User.name == "patrick")).first()
```

Above, the SELECT we asked to emit was preceded by a DELETE, which indicated
the pending deletion for `patrick` proceeded.  There was also a `SELECT`
against the `address` table, which was prompted by the ORM looking for rows
in this table which may be related to the target row; this behavior is part of
a behavior known as {term}`cascade`, and can be tailored to work more
efficiently by allowing the database to handle related rows in `address`
automatically; the section {ref}`cascade_delete` has all the detail on this.

:::{seealso}
{ref}`cascade_delete` - describes how to tune the behavior of
{meth}`~sqlalchemy.orm.Session.delete` in terms of how related rows in other tables
should be handled.
:::

Beyond that, the `patrick` object instance now being deleted is no longer
considered to be persistent within the {class}`~sqlalchemy.orm.Session`, as is shown
by the containment check:

```{code-cell} ipython3
patrick in session
```

However just like the UPDATEs we made to the `sandy` object, every change
we've made here is local to an ongoing transaction, which won't become
permanent if we don't commit it.  As rolling the transaction back is actually
more interesting at the moment, we will do that in the next section.

(sqlatutorial:orm-enabled-delete)=

### ORM-enabled DELETE Statements

Like UPDATE operations, there is also an ORM-enabled version of DELETE which we can
illustrate by using the {func}`~sqlalchemy.sql.expression.delete` construct with
{meth}`~sqlalchemy.orm.Session.execute`.  It also has a feature by which **non expired**
objects (see {term}`expired`) that match the given deletion criteria will be
automatically marked as "{term}`deleted`" in the {class}`~sqlalchemy.orm.Session`:

```{code-cell} ipython3
# refresh the target object for demonstration purposes
# only, not needed for the DELETE
squidward = session.get(User, 4)
session.execute(delete(User).where(User.name == "squidward"))
```

The `squidward` identity, like that of `patrick`, is now also in a
deleted state.   Note that we had to re-load `squidward` above in order
to demonstrate this; if the object were expired, the DELETE operation
would not take the time to refresh expired objects just to see that they
had been deleted:

```{code-cell} ipython3
squidward in session
```

## Rolling Back

The {class}`~sqlalchemy.orm.Session` has a {meth}`~sqlalchemy.orm.Session.rollback` method that as
expected emits a ROLLBACK on the SQL connection in progress.  However, it also
has an effect on the objects that are currently associated with the
{class}`~sqlalchemy.orm.Session`, in our previous example the Python object `sandy`.
While we changed the `.fullname` of the `sandy` object to read `"Sandy
Squirrel"`, we want to roll back this change.   Calling
{meth}`~sqlalchemy.orm.Session.rollback` will not only roll back the transaction but also
**expire** all objects currently associated with this {class}`~sqlalchemy.orm.Session`,
which will have the effect that they will refresh themselves when next accessed
using a process known as {term}`lazy loading`:

```{code-cell} ipython3
session.rollback()
```

To view the "expiration" process more closely, we may observe that the
Python object `sandy` has no state left within its Python `__dict__`,
with the exception of a special SQLAlchemy internal state object:

```{code-cell} ipython3
sandy.__dict__
```

This is the "{term}`expired`" state; accessing the attribute again will autobegin
a new transaction and refresh `sandy` with the current database row:

```{code-cell} ipython3
sandy.fullname
```

We may now observe that the full database row was also populated into the
`__dict__` of the `sandy` object:

```{code-cell} ipython3
sandy.__dict__
```

For deleted objects, when we earlier noted that `patrick` was no longer
in the session, that object's identity is also restored:

```{code-cell} ipython3
patrick in session
```

and of course the database data is present again as well:

```{code-cell} ipython3
session.execute(select(User).where(User.name == 'patrick')).scalar_one() is patrick
```

## Closing a Session

Within the above sections we used a {class}`~sqlalchemy.orm.Session` object outside
of a Python context manager, that is, we didn't use the `with` statement.
That's fine, however if we are doing things this way, it's best that we explicitly
close out the {class}`~sqlalchemy.orm.Session` when we are done with it:

```{code-cell} ipython3
session.close()
```

Closing the {class}`~sqlalchemy.orm.Session`, which is what happens when we use it in
a context manager as well, accomplishes the following things:

- It {term}`releases` all connection resources to the connection pool, cancelling
  out (e.g. rolling back) any transactions that were in progress.

This means that when we make use of a session to perform some read-only
tasks and then close it, we don't need to explicitly call upon
{meth}`~sqlalchemy.orm.Session.rollback` to make sure the transaction is rolled back;
the connection pool handles this.

- It **expunges** all objects from the {class}`~sqlalchemy.orm.Session`.

This means that all the Python objects we had loaded for this {class}`~sqlalchemy.orm.Session`,
like `sandy`, `patrick` and `squidward`, are now in a state known
as {term}`detached`.  In particular, we will note that objects that were still
in an {term}`expired` state, for example due to the call to {meth}`~sqlalchemy.orm.Session.commit`,
are now non-functional, as they don't contain the state of a current row and
are no longer associated with any database transaction in which to be
refreshed:

```{code-cell} ipython3
:tags: [raises-exception]

squidward.name
```

The detached objects can be re-associated with the same, or a new
{class}`~sqlalchemy.orm.Session` using the {meth}`~sqlalchemy.orm.Session.add` method, which
will re-establish their relationship with their particular database row:

```{code-cell} ipython3
session.add(squidward)
squidward.name
```

:::{tip}
Try to avoid using objects in their detached state, if possible. When the
{class}`~sqlalchemy.orm.Session` is closed, clean up references to all the
previously attached objects as well.   For cases where detached objects
are necessary, typically the immediate display of just-committed objects
for a web application where the {class}`~sqlalchemy.orm.Session` is closed before
the view is rendered, set the {paramref}`~sqlalchemy.orm.Session.expire_on_commit`
flag to `False`.
:::
