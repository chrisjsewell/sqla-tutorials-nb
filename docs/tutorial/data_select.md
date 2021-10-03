---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

(sqlatutorial:selecting-data)=

# Selecting Rows with Core or ORM

For both Core and ORM, the {func}`~sqlalchemy.sql.expression.select` function generates a {class}`~sqlalchemy.sql.expression.Select` construct which is used for all SELECT queries.
Passed to methods like {meth}`~sqlalchemy.future.Connection.execute` in Core and
{meth}`~sqlalchemy.orm.Session.execute` in ORM, a SELECT statement is emitted in the current transaction and the result rows available via the returned
{class}`~sqlalchemy.engine.Result` object.

:::{div} orm-header

**ORM Readers** - the content here applies equally well to both Core and ORM
use and basic ORM variant use cases are mentioned here.  However there are
a lot more ORM-specific features available as well; these are documented
at {ref}`queryguide_toplevel`.
:::

```{code-cell} ipython3
:tags: [hide-output]

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey, insert
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()

user_table = Table(
    "user_account",
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(30)),
    Column('fullname', String)
)

class User(Base):
    __table__ = user_table
    def __repr__(self):
        return f"User({self.name!r}, {self.fullname!r})"

address_table = Table(
    "address",
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', ForeignKey('user_account.id'), nullable=False),
    Column('email_address', String, nullable=False)
)

class Address(Base):
    __table__ = address_table
    def __repr__(self):
        return f"Address({self.email_address!r})"

engine = create_engine("sqlite+pysqlite:///:memory:", echo=True, future=True)
Base.metadata.create_all(engine)

with engine.begin() as conn:
    conn.execute(
        insert(user_table),
        [
            {"id": 1, "name": "spongebob", "fullname": "Spongebob Squarepants"},
            {"id": 2, "name": "sandy", "fullname": "Sandy Cheeks"},
            {"id": 3, "name": "patrick", "fullname": "Patrick Star"}
        ]
    )
with engine.begin() as conn:
    conn.execute(
        insert(address_table),
        [
            {"user_id": 1, "email_address": "spongebob@sqlalchemy.org"},
            {"user_id": 2, "email_address": "sandy@sqlalchemy.org"},
            {"user_id": 2, "email_address": "sandy@squirrelpower.org"},
        ]
    )
```

## The select() SQL Expression Construct

The {func}`~sqlalchemy.sql.expression.select` construct builds up a statement in the same way
as that of {func}`~sqlalchemy.sql.expression.insert`, using a {term}`generative` approach where
each method builds more state onto the object.  Like the other SQL constructs,
it can be stringified in place:

```{code-cell} ipython3
from sqlalchemy import select
stmt = select(user_table).where(user_table.c.name == 'spongebob')
print(stmt)
```

Also in the same manner as all other statement-level SQL constructs, to
actually run the statement we pass it to an execution method.
Since a SELECT statement returns
rows we can always iterate the result object to get {class}`~sqlalchemy.engine.Row`
objects back:

```{code-cell} ipython3
with engine.connect() as conn:
    for row in conn.execute(stmt):
        print(row)
```

When using the ORM, particularly with a {func}`~sqlalchemy.sql.expression.select` construct that's
composed against ORM entities, we will want to execute it using the
{meth}`~sqlalchemy.orm.Session.execute` method on the {class}`~sqlalchemy.orm.Session`; using
this approach, we continue to get {class}`~sqlalchemy.engine.Row` objects from the
result, however these rows are now capable of including
complete entities, such as instances of the `User` class, as individual
elements within each row:

```{code-cell} ipython3
stmt = select(User).where(User.name == 'spongebob')
with Session(engine) as session:
    for row in session.execute(stmt):
        print(row)
```

:::{admonition} select() from a Table vs. ORM class
While the SQL generated in these examples looks the same whether we invoke
`select(user_table)` or `select(User)`, in the more general case
they do not necessarily render the same thing, as an ORM-mapped class
may be mapped to other kinds of "selectables" besides tables.  The
`select()` that's against an ORM entity also indicates that ORM-mapped
instances should be returned in a result, which is not the case when
SELECTing from a {class}`~sqlalchemy.schema.Table` object.
:::

The following sections will discuss the SELECT construct in more detail.

## Setting the COLUMNS and FROM clause

The {func}`~sqlalchemy.sql.expression.select` function accepts positional elements representing any
number of {class}`~sqlalchemy.schema.Column` and/or {class}`~sqlalchemy.schema.Table` expressions, as
well as a wide range of compatible objects, which are resolved into a list of SQL
expressions to be SELECTed from that will be returned as columns in the result
set.  These elements also serve in simpler cases to create the FROM clause,
which is inferred from the columns and table-like expressions passed:

```{code-cell} ipython3
print(select(user_table))
```

To SELECT from individual columns using a Core approach,
{class}`~sqlalchemy.schema.Column` objects are accessed from the {attr}`~sqlalchemy.schema.Table.c`
accessor and can be sent directly; the FROM clause will be inferred as the set
of all {class}`~sqlalchemy.schema.Table` and other {class}`~sqlalchemy.sql.expression.FromClause` objects that
are represented by those columns:

```{code-cell} ipython3
print(select(user_table.c.name, user_table.c.fullname))
```

(sqlatutorial:selecting-orm-entities)=

### Selecting ORM Entities and Columns

ORM entities, such our `User` class as well as the column-mapped
attributes upon it such as `User.name`, also participate in the SQL Expression
Language system representing tables and columns.    Below illustrates an
example of SELECTing from the `User` entity, which ultimately renders
in the same way as if we had used `user_table` directly:

```{code-cell} ipython3
print(select(User))
```

When executing a statement like the above using the ORM {meth}`~sqlalchemy.orm.Session.execute`
method, there is an important difference when we select from a full entity
such as `User`, as opposed to `user_table`, which is that the **entity
itself is returned as a single element within each row**.  That is, when we fetch rows from
the above statement, as there is only the `User` entity in the list of
things to fetch, we get back {class}`~sqlalchemy.engine.Row` objects that have only one element, which contain
instances of the `User` class:

```{code-cell} ipython3
row = session.execute(select(User)).first()
row
```

The above {class}`~sqlalchemy.engine.Row` has just one element, representing the `User` entity:

```{code-cell} ipython3
row[0]
```

Alternatively, we can select individual columns of an ORM entity as distinct
elements within result rows, by using the class-bound attributes; when these
are passed to a construct such as {func}`~sqlalchemy.sql.expression.select`, they are resolved into
the {class}`~sqlalchemy.schema.Column` or other SQL expression represented by each
attribute:

```{code-cell} ipython3
print(select(User.name, User.fullname))
```

When we invoke *this* statement using {meth}`~sqlalchemy.orm.Session.execute`, we now
receive rows that have individual elements per value, each corresponding
to a separate column or other SQL expression:

```{code-cell} ipython3
row = session.execute(select(User.name, User.fullname)).first()
row
```

The approaches can also be mixed, as below where we SELECT the `name`
attribute of the `User` entity as the first element of the row, and combine
it with full `Address` entities in the second element:

```{code-cell} ipython3
session.execute(
    select(User.name, Address).
    where(User.id==Address.user_id).
    order_by(Address.id)
).all()
```

Approaches towards selecting ORM entities and columns as well as common methods
for converting rows are discussed further at {ref}`orm_queryguide_select_columns`.

:::{seealso}
{ref}`orm_queryguide_select_columns` - in the {ref}`queryguide_toplevel`
:::

### Selecting from Labeled SQL Expressions

The {meth}`~sqlalchemy.sql.expression.ColumnElement.label` method as well as the same-named method
available on ORM attributes provides a SQL label of a column or expression,
allowing it to have a specific name in a result set.  This can be helpful
when referring to arbitrary SQL expressions in a result row by name:

```{code-cell} ipython3
from sqlalchemy import func, cast
stmt = (
    select(
        ("Username: " + user_table.c.name).label("username"),
    ).order_by(user_table.c.name)
)
with engine.connect() as conn:
    for row in conn.execute(stmt):
        print(f"{row.username}")
```

:::{seealso}
{ref}`sqlatutorial:order-by-label` - the label names we create may also be
referred towards in the ORDER BY or GROUP BY clause of the {class}`~sqlalchemy.sql.expression.Select`.
:::

(sqlatutorial:select-arbtrary-text)=

### Selecting with Textual Column Expressions

When we construct a {class}`~sqlalchemy.sql.expression.Select` object using the {func}`~sqlalchemy.sql.expression.select`
function, we are normally passing to it a series of {class}`~sqlalchemy.schema.Table`
and {class}`~sqlalchemy.schema.Column` objects that were defined using
{ref}`table metadata <sqlatutorial:working-with-metadata>`, or when using the ORM we may be
sending ORM-mapped attributes that represent table columns.   However,
sometimes there is also the need to manufacture arbitrary SQL blocks inside
of statements, such as constant string expressions, or just some arbitrary
SQL that's quicker to write literally.

The {func}`~sqlalchemy.sql.expression.text` construct introduced at
{ref}`sqlatutorial:working-with-transactions` can in fact be embedded into a
{class}`~sqlalchemy.sql.expression.Select` construct directly, such as below where we manufacture
a hardcoded string literal `'some label'` and embed it within the
SELECT statement:

```{code-cell} ipython3
from sqlalchemy import text
stmt = (
    select(
        text("'some phrase'"), user_table.c.name
    ).order_by(user_table.c.name)
)
with engine.connect() as conn:
    print(conn.execute(stmt).all())
```

While the {func}`~sqlalchemy.sql.expression.text` construct can be used in most places to inject
literal SQL phrases, more often than not we are actually dealing with textual
units that each represent an individual
column expression.  In this common case we can get more functionality out of
our textual fragment using the {func}`~sqlalchemy.sql.expression.literal_column`
construct instead.  This object is similar to {func}`~sqlalchemy.sql.expression.text` except that
instead of representing arbitrary SQL of any form,
it explicitly represents a single "column" and can then be labeled and referred
towards in subqueries and other expressions:

```{code-cell} ipython3
from sqlalchemy import literal_column
stmt = (
    select(
        literal_column("'some phrase'").label("p"), user_table.c.name
    ).order_by(user_table.c.name)
)
with engine.connect() as conn:
    for row in conn.execute(stmt):
        print(f"{row.p}, {row.name}")
```

Note that in both cases, when using {func}`~sqlalchemy.sql.expression.text` or
{func}`~sqlalchemy.sql.expression.literal_column`, we are writing a syntactical SQL expression, and
not a literal value. We therefore have to include whatever quoting or syntaxes
are necessary for the SQL we want to see rendered.

(sqlatutorial:select-where-clause)=

## The WHERE clause

SQLAlchemy allows us to compose SQL expressions, such as `name = 'squidward'`
or `user_id > 10`, by making use of standard Python operators in
conjunction with
{class}`~sqlalchemy.schema.Column` and similar objects.   For boolean expressions, most
Python operators such as `==`, `!=`, `<`, `>=` etc. generate new
SQL Expression objects, rather than plain boolean `True`/`False` values:

```{code-cell} ipython3
print(user_table.c.name == 'squidward')
print(address_table.c.user_id > 10)
```

We can use expressions like these to generate the WHERE clause by passing
the resulting objects to the {meth}`~sqlalchemy.sql.expression.Select.where` method:

```{code-cell} ipython3
print(select(user_table).where(user_table.c.name == 'squidward'))
```

To produce multiple expressions joined by AND, the {meth}`~sqlalchemy.sql.expression.Select.where`
method may be invoked any number of times:

```{code-cell} ipython3
print(
    select(address_table.c.email_address).
    where(user_table.c.name == 'squidward').
    where(address_table.c.user_id == user_table.c.id)
)
```

A single call to {meth}`~sqlalchemy.sql.expression.Select.where` also accepts multiple expressions
with the same effect:

```{code-cell} ipython3
print(
    select(address_table.c.email_address).
    where(
         user_table.c.name == 'squidward',
         address_table.c.user_id == user_table.c.id
    )
)
```

"AND" and "OR" conjunctions are both available directly using the
{func}`~sqlalchemy.sql.expression.and_` and {func}`~sqlalchemy.sql.expression.or_` functions, illustrated below in terms
of ORM entities:

```{code-cell} ipython3
from sqlalchemy import and_, or_
print(
    select(Address.email_address).
    where(
        and_(
            or_(User.name == 'squidward', User.name == 'sandy'),
            Address.user_id == User.id
        )
    )
)
```

For simple "equality" comparisons against a single entity, there's also a
popular method known as {meth}`~sqlalchemy.sql.expression.Select.filter_by` which accepts keyword
arguments that match to column keys or ORM attribute names.  It will filter
against the leftmost FROM clause or the last entity joined:

```{code-cell} ipython3
print(
    select(User).filter_by(name='spongebob', fullname='Spongebob Squarepants')
)
```

:::{seealso}
{doc}`core/operators` - descriptions of most SQL operator functions in SQLAlchemy
:::

(sqlatutorial:select-join)=

## Explicit FROM clauses and JOINs

As mentioned previously, the FROM clause is usually **inferred**
based on the expressions that we are setting in the columns
clause as well as other elements of the {class}`~sqlalchemy.sql.expression.Select`.

If we set a single column from a particular {class}`~sqlalchemy.schema.Table`
in the COLUMNS clause, it puts that {class}`~sqlalchemy.schema.Table` in the FROM
clause as well:

```{code-cell} ipython3
print(select(user_table.c.name))
```

If we were to put columns from two tables, then we get a comma-separated FROM
clause:

```{code-cell} ipython3
print(select(user_table.c.name, address_table.c.email_address))
```

In order to JOIN these two tables together, we typically use one of two methods
on {class}`~sqlalchemy.sql.expression.Select`.  The first is the {meth}`~sqlalchemy.sql.expression.Select.join_from`
method, which allows us to indicate the left and right side of the JOIN
explicitly:

```{code-cell} ipython3
print(
    select(user_table.c.name, address_table.c.email_address).
    join_from(user_table, address_table)
)
```

The other is the the {meth}`~sqlalchemy.sql.expression.Select.join` method, which indicates only the
right side of the JOIN, the left hand-side is inferred:

```{code-cell} ipython3
print(
    select(user_table.c.name, address_table.c.email_address).
    join(address_table)
)
```

:::{admonition} The ON Clause is inferred
When using {meth}`~sqlalchemy.sql.expression.Select.join_from` or {meth}`~sqlalchemy.sql.expression.Select.join`, we may
observe that the ON clause of the join is also inferred for us in simple
foreign key cases. More on that in the next section.
:::

We also have the option to add elements to the FROM clause explicitly, if it is not
inferred the way we want from the columns clause.  We use the
{meth}`~sqlalchemy.sql.expression.Select.select_from` method to achieve this, as below
where we establish `user_table` as the first element in the FROM
clause and {meth}`~sqlalchemy.sql.expression.Select.join` to establish `address_table` as
the second:

```{code-cell} ipython3
print(
    select(address_table.c.email_address).
    select_from(user_table).join(address_table)
)
```

Another example where we might want to use {meth}`~sqlalchemy.sql.expression.Select.select_from`
is if our columns clause doesn't have enough information to provide for a
FROM clause.  For example, to SELECT from the common SQL expression
`count(*)`, we use a SQLAlchemy element known as {data}`~sqlalchemy.sql.expression.func` to
produce the SQL `count()` function:

```{code-cell} ipython3
from sqlalchemy import func
print (
    select(func.count('*')).select_from(user_table)
)
```

:::{seealso}
{ref}`orm_queryguide_select_from` - in the {ref}`queryguide_toplevel` -
contains additional examples and notes
regarding the interaction of {meth}`~sqlalchemy.sql.expression.Select.select_from` and
{meth}`~sqlalchemy.sql.expression.Select.join`.
:::

(sqlatutorial:select-join-onclause)=

### Setting the ON Clause

The previous examples of JOIN illustrated that the {class}`~sqlalchemy.sql.expression.Select` construct
can join between two tables and produce the ON clause automatically.  This
occurs in those examples because the `user_table` and `address_table`
{class}`~sqlalchemy.schema.Table` objects include a single {class}`~sqlalchemy.schema.ForeignKeyConstraint`
definition which is used to form this ON clause.

If the left and right targets of the join do not have such a constraint, or
there are multiple constraints in place, we need to specify the ON clause
directly.   Both {meth}`~sqlalchemy.sql.expression.Select.join` and {meth}`~sqlalchemy.sql.expression.Select.join_from`
accept an additional argument for the ON clause, which is stated using the
same SQL Expression mechanics as we saw about in {ref}`sqlatutorial:select-where-clause`:

```{code-cell} ipython3
print(
    select(address_table.c.email_address).
    select_from(user_table).
    join(address_table, user_table.c.id == address_table.c.user_id)
)
```

:::{div} orm-header

**ORM Tip** - there's another way to generate the ON clause when using
ORM entities that make use of the {func}`~sqlalchemy.orm.relationship` construct,
like the mapping set up in the previous section at
{ref}`sqlatutorial:declaring-mapped-classes`.
This is a whole subject onto itself, which is introduced at length
at {ref}`sqlatutorial:joining-relationships`.
:::

### OUTER and FULL join

Both the {meth}`~sqlalchemy.sql.expression.Select.join` and {meth}`~sqlalchemy.sql.expression.Select.join_from` methods
accept keyword arguments {paramref}`~sqlalchemy.sql.expression.Select.join.isouter` and
{paramref}`~sqlalchemy.sql.expression.Select.join.full` which will render LEFT OUTER JOIN
and FULL OUTER JOIN, respectively:

```{code-cell} ipython3
print(
    select(user_table).join(address_table, isouter=True)
)
print(
    select(user_table).join(address_table, full=True)
)
```

There is also a method {meth}`~sqlalchemy.sql.expression.Select.outerjoin` that is equivalent to
using `.join(..., isouter=True)`.

:::{tip}
SQL also has a "RIGHT OUTER JOIN".  SQLAlchemy doesn't render this directly;
instead, reverse the order of the tables and use "LEFT OUTER JOIN".
:::

(sqlatutorial:order-by-group-by-having)=

## ORDER BY, GROUP BY, HAVING

The SELECT SQL statement includes a clause called ORDER BY which is used to
return the selected rows within a given ordering.

The GROUP BY clause is constructed similarly to the ORDER BY clause, and has
the purpose of sub-dividing the selected rows into specific groups upon which
aggregate functions may be invoked. The HAVING clause is usually used with
GROUP BY and is of a similar form to the WHERE clause, except that it's applied
to the aggregated functions used within groups.

(sqlatutorial:order-by)=

### ORDER BY

The ORDER BY clause is constructed in terms
of SQL Expression constructs typically based on {class}`~sqlalchemy.schema.Column` or
similar objects.  The {meth}`~sqlalchemy.sql.expression.Select.order_by` method accepts one or
more of these expressions positionally:

```{code-cell} ipython3
print(select(user_table).order_by(user_table.c.name))
```

Ascending / descending is available from the {meth}`~sqlalchemy.sql.expression.ColumnElement.asc`
and {meth}`~sqlalchemy.sql.expression.ColumnElement.desc` modifiers, which are present
from ORM-bound attributes as well:

```{code-cell} ipython3
print(select(User).order_by(User.fullname.desc()))
```

The above statement will yield rows that are sorted by the
`user_account.fullname` column in descending order.

(sqlatutorial:group-by-w-aggregates)=

### Aggregate functions with GROUP BY / HAVING

In SQL, aggregate functions allow column expressions across multiple rows
to be aggregated together to produce a single result.  Examples include
counting, computing averages, as well as locating the maximum or minimum
value in a set of values.

SQLAlchemy provides for SQL functions in an open-ended way using a namespace
known as {data}`~sqlalchemy.sql.expression.func`.  This is a special constructor object which
will create new instances of {class}`~sqlalchemy.sql.functions.Function` when given the name
of a particular SQL function, which can have any name, as well as zero or
more arguments to pass to the function, which are, like in all other cases,
SQL Expression constructs.   For example, to
render the SQL COUNT() function against the `user_account.id` column,
we call upon the `count()` name:

```{code-cell} ipython3
from sqlalchemy import func
count_fn = func.count(user_table.c.id)
print(count_fn)
```

SQL functions are described in more detail later in this tutorial at
{ref}`sqlatutorial:functions`.

When using aggregate functions in SQL, the GROUP BY clause is essential in that
it allows rows to be partitioned into groups where aggregate functions will
be applied to each group individually.  When requesting non-aggregated columns
in the COLUMNS clause of a SELECT statement, SQL requires that these columns
all be subject to a GROUP BY clause, either directly or indirectly based on
a primary key association.    The HAVING clause is then used in a similar
manner as the WHERE clause, except that it filters out rows based on aggregated
values rather than direct row contents.

SQLAlchemy provides for these two clauses using the {meth}`~sqlalchemy.sql.expression.Select.group_by`
and {meth}`~sqlalchemy.sql.expression.Select.having` methods.   Below we illustrate selecting
user name fields as well as count of addresses, for those users that have more
than one address:

```{code-cell} ipython3
with engine.connect() as conn:
    result = conn.execute(
        select(User.name, func.count(Address.id).label("count")).
        join(Address).
        group_by(User.name).
        having(func.count(Address.id) > 1)
    )
    print(result.all())
```

(sqlatutorial:order-by-label)=

### Ordering or Grouping by a Label

An important technique, in particular on some database backends, is the ability
to ORDER BY or GROUP BY an expression that is already stated in the columns
clause, without re-stating the expression in the ORDER BY or GROUP BY clause
and instead using the column name or labeled name from the COLUMNS clause.
This form is available by passing the string text of the name to the
{meth}`~sqlalchemy.sql.expression.Select.order_by` or {meth}`~sqlalchemy.sql.expression.Select.group_by` method.  The text
passed is **not rendered directly**; instead, the name given to an expression
in the columns clause and rendered as that expression name in context, raising an
error if no match is found.
The unary modifiers {func}`~sqlalchemy.sql.expression.asc` and {func}`~sqlalchemy.sql.expression.desc` may also be used in this form:

```{code-cell} ipython3
from sqlalchemy import func, desc
stmt = select(
        Address.user_id,
        func.count(Address.id).label('num_addresses')).\
        group_by("user_id").order_by("user_id", desc("num_addresses"))
print(stmt)
```

(sqlatutorial:using-aliases)=

## Using Aliases

Now that we are selecting from multiple tables and using joins, we quickly
run into the case where we need to refer to the same table mutiple times
in the FROM clause of a statement.  We accomplish this using SQL **aliases**,
which are a syntax that supplies an alternative name to a table or subquery
from which it can be referred towards in the statement.

In the SQLAlchemy Expression Language, these "names" are instead represented by
{class}`~sqlalchemy.sql.expression.FromClause` objects known as the {class}`~sqlalchemy.sql.expression.Alias` construct,
which is constructed in Core using the {meth}`~sqlalchemy.sql.expression.FromClause.alias`
method. An {class}`~sqlalchemy.sql.expression.Alias` construct is just like a {class}`~sqlalchemy.schema.Table`
construct in that it also has a namespace of {class}`~sqlalchemy.schema.Column`
objects within the `Alias.c` collection.  The SELECT statement
below for example returns all unique pairs of user names:

```{code-cell} ipython3
user_alias_1 = user_table.alias()
user_alias_2 = user_table.alias()
print(
    select(user_alias_1.c.name, user_alias_2.c.name).
    join_from(user_alias_1, user_alias_2, user_alias_1.c.id > user_alias_2.c.id)
)
```

(sqlatutorial:orm-entity-aliases)=

### ORM Entity Aliases

The ORM equivalent of the {meth}`~sqlalchemy.sql.expression.FromClause.alias` method is the
ORM {func}`~sqlalchemy.orm.aliased` function, which may be applied to an entity
such as `User` and `Address`.  This produces a {class}`~sqlalchemy.sql.expression.Alias` object
internally that's against the original mapped {class}`~sqlalchemy.schema.Table` object,
while maintaining ORM functionality.  The SELECT below selects from the
`User` entity all objects that include two particular email addresses:

```{code-cell} ipython3
from sqlalchemy.orm import aliased
address_alias_1 = aliased(Address)
address_alias_2 = aliased(Address)
print(
    select(User).
    join_from(User, address_alias_1).
    where(address_alias_1.email_address == 'patrick@aol.com').
    join_from(User, address_alias_2).
    where(address_alias_2.email_address == 'patrick@gmail.com')
)
```

:::{tip}
As mentioned in {ref}`sqlatutorial:select-join-onclause`, the ORM provides
for another way to join using the {func}`~sqlalchemy.orm.relationship` construct.
The above example using aliases is demonstrated using {func}`~sqlalchemy.orm.relationship`
at {ref}`sqlatutorial:joining-relationships-aliased`.
:::

(sqlatutorial:subqueries-ctes)=

## Subqueries and CTEs

A subquery in SQL is a SELECT statement that is rendered within parenthesis and
placed within the context of an enclosing statement, typically a SELECT
statement but not necessarily.

This section will cover a so-called "non-scalar" subquery, which is typically
placed in the FROM clause of an enclosing SELECT.   We will also cover the
Common Table Expression or CTE, which is used in a similar way as a subquery,
but includes additional features.

SQLAlchemy uses the {class}`~sqlalchemy.sql.expression.Subquery` object to represent a subquery and
the {class}`~sqlalchemy.sql.expression.CTE` to represent a CTE, usually obtained from the
{meth}`~sqlalchemy.sql.expression.Select.subquery` and {meth}`~sqlalchemy.sql.expression.Select.cte` methods, respectively.
Either object can be used as a FROM element inside of a larger
{func}`~sqlalchemy.sql.expression.select` construct.

We can construct a {class}`~sqlalchemy.sql.expression.Subquery` that will select an aggregate count
of rows from the `address` table (aggregate functions and GROUP BY were
introduced previously at {ref}`sqlatutorial:group-by-w-aggregates`):

```{code-cell} ipython3
subq = select(
    func.count(address_table.c.id).label("count"),
    address_table.c.user_id
).group_by(address_table.c.user_id).subquery()
```

Stringifying the subquery by itself without it being embedded inside of another
{class}`~sqlalchemy.sql.expression.Select` or other statement produces the plain SELECT statement
without any enclosing parenthesis:

```{code-cell} ipython3
print(subq)
```

The {class}`~sqlalchemy.sql.expression.Subquery` object behaves like any other FROM object such as a {class}`~sqlalchemy.schema.Table`,
notably that it includes a `Subquery.c` namespace of the columns which it selects.
We can use this namespace to refer to both the `user_id` column as well as our custom labeled `count` expression:

```{code-cell} ipython3
print(select(subq.c.user_id, subq.c.count))
```

With a selection of rows contained within the `subq` object, we can apply
the object to a larger {class}`~sqlalchemy.sql.expression.Select` that will join the data to
the `user_account` table:

```{code-cell} ipython3
stmt = select(
   user_table.c.name,
   user_table.c.fullname,
   subq.c.count
).join_from(user_table, subq)

print(stmt)
```

In order to join from `user_account` to `address`, we made use of the
{meth}`~sqlalchemy.sql.expression.Select.join_from` method.   As has been illustrated previously, the
ON clause of this join was again **inferred** based on foreign key constraints.
Even though a SQL subquery does not itself have any constraints, SQLAlchemy can
act upon constraints represented on the columns by determining that the
`subq.c.user_id` column is **derived** from the `address_table.c.user_id`
column, which does express a foreign key relationship back to the
`user_table.c.id` column which is then used to generate the ON clause.

### Common Table Expressions (CTEs)

Usage of the {class}`~sqlalchemy.sql.expression.CTE` construct in SQLAlchemy is virtually
the same as how the {class}`~sqlalchemy.sql.expression.Subquery` construct is used.  By changing
the invocation of the {meth}`~sqlalchemy.sql.expression.Select.subquery` method to use
{meth}`~sqlalchemy.sql.expression.Select.cte` instead, we can use the resulting object as a FROM
element in the same way, but the SQL rendered is the very different common
table expression syntax:

```{code-cell} ipython3
subq = select(
    func.count(address_table.c.id).label("count"),
    address_table.c.user_id
).group_by(address_table.c.user_id).cte()

stmt = select(
   user_table.c.name,
   user_table.c.fullname,
   subq.c.count
).join_from(user_table, subq)

print(stmt)
```

The {class}`~sqlalchemy.sql.expression.CTE` construct also features the ability to be used
in a "recursive" style, and may in more elaborate cases be composed from the
RETURNING clause of an INSERT, UPDATE or DELETE statement.  The docstring
for {class}`~sqlalchemy.sql.expression.CTE` includes details on these additional patterns.

In both cases, the subquery and CTE were named at the SQL level using an
"anonymous" name.  In the Python code, we don't need to provide these names
at all.  The object identity of the {class}`~sqlalchemy.sql.expression.Subquery` or {class}`~sqlalchemy.sql.expression.CTE`
instances serves as the syntactical identity of the object when rendered.
A name that will be rendered in the SQL can be provided by passing it as the
first argument of the {meth}`~sqlalchemy.sql.expression.Select.subquery` or {meth}`~sqlalchemy.sql.expression.Select.cte` methods.

:::{seealso}
{meth}`~sqlalchemy.sql.expression.Select.subquery` - further detail on subqueries

{meth}`~sqlalchemy.sql.expression.Select.cte` - examples for CTE including how to use
RECURSIVE as well as DML-oriented CTEs
:::

### ORM Entity Subqueries/CTEs

In the ORM, the {func}`~sqlalchemy.orm.aliased` construct may be used to associate an ORM
entity, such as our `User` or `Address` class, with any {class}`~sqlalchemy.sql.expression.FromClause`
concept that represents a source of rows.  The preceding section
{ref}`sqlatutorial:orm-entity-aliases` illustrates using {func}`~sqlalchemy.orm.aliased`
to associate the mapped class with an {class}`~sqlalchemy.sql.expression.Alias` of its
mapped {class}`~sqlalchemy.schema.Table`.   Here we illustrate {func}`~sqlalchemy.orm.aliased` doing the same
thing against both a {class}`~sqlalchemy.sql.expression.Subquery` as well as a {class}`~sqlalchemy.sql.expression.CTE`
generated against a {class}`~sqlalchemy.sql.expression.Select` construct, that ultimately derives
from that same mapped {class}`~sqlalchemy.schema.Table`.

Below is an example of applying {func}`~sqlalchemy.orm.aliased` to the {class}`~sqlalchemy.sql.expression.Subquery`
construct, so that ORM entities can be extracted from its rows.  The result
shows a series of `User` and `Address` objects, where the data for
each `Address` object ultimately came from a subquery against the
`address` table rather than that table directly:

```{code-cell} ipython3
subq = select(Address).where(~Address.email_address.like('%@aol.com')).subquery()
address_subq = aliased(Address, subq)
stmt = select(User, address_subq).join_from(User, address_subq).order_by(User.id, address_subq.id)
with Session(engine) as session:
    for user, address in session.execute(stmt):
        print(f"{user} {address}")
```

Another example follows, which is exactly the same except it makes use of the
{class}`~sqlalchemy.sql.expression.CTE` construct instead:

```{code-cell} ipython3
cte = select(Address).where(~Address.email_address.like('%@aol.com')).cte()
address_cte = aliased(Address, cte)
stmt = select(User, address_cte).join_from(User, address_cte).order_by(User.id, address_cte.id)
with Session(engine) as session:
    for user, address in session.execute(stmt):
        print(f"{user} {address}")
```

(sqlatutorial:scalar-subquery)=

## Scalar and Correlated Subqueries

A scalar subquery is a subquery that returns exactly zero or one row and
exactly one column.  The subquery is then used in the COLUMNS or WHERE clause
of an enclosing SELECT statement and is different than a regular subquery in
that it is not used in the FROM clause.   A {term}`correlated subquery` is a
scalar subquery that refers to a table in the enclosing SELECT statement.

SQLAlchemy represents the scalar subquery using the
{class}`~sqlalchemy.sql.expression.ScalarSelect` construct, which is part of the
{class}`~sqlalchemy.sql.expression.ColumnElement` expression hierarchy, in contrast to the regular
subquery which is represented by the {class}`~sqlalchemy.sql.expression.Subquery` construct, which is
in the {class}`~sqlalchemy.sql.expression.FromClause` hierarchy.

Scalar subqueries are often, but not necessarily, used with aggregate functions,
introduced previously at {ref}`sqlatutorial:group-by-w-aggregates`.   A scalar
subquery is indicated explicitly by making use of the {meth}`~sqlalchemy.sql.expression.Select.scalar_subquery`
method as below.  It's default string form when stringified by itself
renders as an ordinary SELECT statement that is selecting from two tables:

```{code-cell} ipython3
subq = select(func.count(address_table.c.id)).\
            where(user_table.c.id == address_table.c.user_id).\
            scalar_subquery()
print(subq)
```

The above `subq` object now falls within the {class}`~sqlalchemy.sql.expression.ColumnElement`
SQL expression hierarchy, in that it may be used like any other column
expression:

```{code-cell} ipython3
print(subq == 5)
```

Although the scalar subquery by itself renders both `user_account` and
`address` in its FROM clause when stringified by itself, when embedding it
into an enclosing {func}`~sqlalchemy.sql.expression.select` construct that deals with the
`user_account` table, the `user_account` table is automatically
**correlated**, meaning it does not render in the FROM clause of the subquery:

```{code-cell} ipython3
stmt = select(user_table.c.name, subq.label("address_count"))
print(stmt)
```

Simple correlated subqueries will usually do the right thing that's desired.
However, in the case where the correlation is ambiguous, SQLAlchemy will let
us know that more clarity is needed:

```{code-cell} ipython3
:tags: [raises-exception]

stmt = select(
    user_table.c.name,
    address_table.c.email_address,
    subq.label("address_count")
).\
join_from(user_table, address_table).\
order_by(user_table.c.id, address_table.c.id)
print(stmt)
```

To specify that the `user_table` is the one we seek to correlate we specify
this using the {meth}`~sqlalchemy.sql.expression.ScalarSelect.correlate` or
{meth}`~sqlalchemy.sql.expression.ScalarSelect.correlate_except` methods:

```{code-cell} ipython3
subq = select(func.count(address_table.c.id)).\
            where(user_table.c.id == address_table.c.user_id).\
            scalar_subquery().correlate(user_table)
```

The statement then can return the data for this column like any other:

```{code-cell} ipython3
with engine.connect() as conn:
    result = conn.execute(
        select(
            user_table.c.name,
            address_table.c.email_address,
            subq.label("address_count")
        ).
        join_from(user_table, address_table).
        order_by(user_table.c.id, address_table.c.id)
    )
    print(result.all())
```

(sqlatutorial:union)=

## UNION, UNION ALL and other set operations

In SQL,SELECT statements can be merged together using the UNION or UNION ALL
SQL operation, which produces the set of all rows produced by one or more
statements together.  Other set operations such as INTERSECT \[ALL\] and
EXCEPT \[ALL\] are also possible.

SQLAlchemy's {class}`~sqlalchemy.sql.expression.Select` construct supports compositions of this
nature using functions like {func}`~sqlalchemy.sql.expression.union`, {func}`~sqlalchemy.sql.expression.intersect` and
{func}`~sqlalchemy.sql.expression.except_`, and the "all" counterparts {func}`~sqlalchemy.sql.expression.union_all`,
{func}`~sqlalchemy.sql.expression.intersect_all` and {func}`~sqlalchemy.sql.expression.except_all`. These functions all
accept an arbitrary number of sub-selectables, which are typically
{class}`~sqlalchemy.sql.expression.Select` constructs but may also be an existing composition.

The construct produced by these functions is the {class}`~sqlalchemy.sql.expression.CompoundSelect`,
which is used in the same manner as the {class}`~sqlalchemy.sql.expression.Select` construct, except
that it has fewer methods.   The {class}`~sqlalchemy.sql.expression.CompoundSelect` produced by
{func}`~sqlalchemy.sql.expression.union_all` for example may be invoked directly using
{meth}`~sqlalchemy.engine.Connection.execute`:

```{code-cell} ipython3
from sqlalchemy import union_all
stmt1 = select(user_table).where(user_table.c.name == 'sandy')
stmt2 = select(user_table).where(user_table.c.name == 'spongebob')
u = union_all(stmt1, stmt2)
with engine.connect() as conn:
    result = conn.execute(u)
    print(result.all())
```

To use a {class}`~sqlalchemy.sql.expression.CompoundSelect` as a subquery, just like {class}`~sqlalchemy.sql.expression.Select`
it provides a {meth}`~sqlalchemy.sql.expression.SelectBase.subquery` method which will produce a
{class}`~sqlalchemy.sql.expression.Subquery` object with a {attr}`~sqlalchemy.sql.expression.FromClause.c`
collection that may be referred towards in an enclosing {func}`~sqlalchemy.sql.expression.select`:

```{code-cell} ipython3
u_subq = u.subquery()
stmt = (
    select(u_subq.c.name, address_table.c.email_address).
    join_from(address_table, u_subq).
    order_by(u_subq.c.name, address_table.c.email_address)
)
with engine.connect() as conn:
    result = conn.execute(stmt)
    print(result.all())
```

(sqlatutorial:exists)=

## EXISTS subqueries

The SQL EXISTS keyword is an operator that is used with {ref}`scalar subqueries <sqlatutorial:scalar-subquery>` to return a boolean true or false depending on if
the SELECT statement would return a row.  SQLAlchemy includes a variant of the
{class}`~sqlalchemy.sql.expression.ScalarSelect` object called {class}`~sqlalchemy.sql.expression.Exists`, which will
generate an EXISTS subquery and is most conveniently generated using the
{meth}`~sqlalchemy.sql.expression.SelectBase.exists` method.  Below we produce an EXISTS so that we
can return `user_account` rows that have more than one related row in
`address`:

```{code-cell} ipython3
subq = (
    select(func.count(address_table.c.id)).
    where(user_table.c.id == address_table.c.user_id).
    group_by(address_table.c.user_id).
    having(func.count(address_table.c.id) > 1)
).exists()
with engine.connect() as conn:
    result = conn.execute(
        select(user_table.c.name).where(subq)
    )
    print(result.all())
```

The EXISTS construct is more often than not used as a negation, e.g. NOT EXISTS,
as it provides a SQL-efficient form of locating rows for which a related
table has no rows.  Below we select user names that have no email addresses;
note the binary negation operator (`~`) used inside the second WHERE
clause:

```{code-cell} ipython3
subq = (
    select(address_table.c.id).
    where(user_table.c.id == address_table.c.user_id)
).exists()
with engine.connect() as conn:
    result = conn.execute(
        select(user_table.c.name).where(~subq)
    )
    print(result.all())
```

(sqlatutorial:functions)=

## Working with SQL Functions

First introduced earlier in this section at
{ref}`sqlatutorial:group-by-w-aggregates`, the {data}`~sqlalchemy.sql.expression.func` object serves as a
factory for creating new {class}`~sqlalchemy.sql.functions.Function` objects, which when used
in a construct like {func}`~sqlalchemy.sql.expression.select`, produce a SQL function display,
typically consisting of a name, some parenthesis (although not always), and
possibly some arguments. Examples of typical SQL functions include:

- the `count()` function, an aggregate function which counts how many
  rows are returned:

```{code-cell} ipython3
print(select(func.count()).select_from(user_table))
```

- the `lower()` function, a string function that converts a string to lower
  case:

```{code-cell} ipython3
print(select(func.lower("A String With Much UPPERCASE")))
```

- the `now()` function, which provides for the current date and time; as this
  is a common function, SQLAlchemy knows how to render this differently for each
  backend, in the case of SQLite using the CURRENT_TIMESTAMP function:

```{code-cell} ipython3
stmt = select(func.now())
with engine.connect() as conn:
    result = conn.execute(stmt)
    print(result.all())
```

As most database backends feature dozens if not hundreds of different SQL
functions, {data}`~sqlalchemy.sql.expression.func` tries to be as liberal as possible in what it
accepts. Any name that is accessed from this namespace is automatically
considered to be a SQL function that will render in a generic way:

```{code-cell} ipython3
print(select(func.some_crazy_function(user_table.c.name, 17)))
```

At the same time, a relatively small set of extremely common SQL functions such
as {class}`~sqlalchemy.sql.functions.count`, {class}`~sqlalchemy.sql.functions.now`, {class}`~sqlalchemy.sql.functions.max`,
{class}`~sqlalchemy.sql.functions.concat` include pre-packaged versions of themselves which
provide for proper typing information as well as backend-specific SQL
generation in some cases.  The example below contrasts the SQL generation
that occurs for the PostgreSQL dialect compared to the Oracle dialect for
the {class}`~sqlalchemy.sql.functions.now` function:

```{code-cell} ipython3
from sqlalchemy.dialects import postgresql
print(select(func.now()).compile(dialect=postgresql.dialect()))
```

```{code-cell} ipython3
from sqlalchemy.dialects import oracle
print(select(func.now()).compile(dialect=oracle.dialect()))
```

### Functions Have Return Types

As functions are column expressions, they also have
SQL {ref}`datatypes <types_toplevel>` that describe the data type of
a generated SQL expression.  We refer to these types here as "SQL return types",
in reference to the type of SQL value that is returned by the function
in the context of a database-side SQL expression,
as opposed to the "return type" of a Python function.

The SQL return type of any SQL function may be accessed, typically for
debugging purposes, by referring to the {attr}`~sqlalchemy.sql.functions.Function.type`
attribute:

```{code-cell} ipython3
func.now().type
```

These SQL return types are significant when making
use of the function expression in the context of a larger expression; that is,
math operators will work better when the datatype of the expression is
something like {class}`~sqlalchemy.types.Integer` or {class}`~sqlalchemy.types.Numeric`, JSON
accessors in order to work need to be using a type such as
{class}`~sqlalchemy.types.JSON`.  Certain classes of functions return entire rows
instead of column values, where there is a need to refer to specific columns;
such functions are referred towards
as {ref}`table valued functions <sqlatutorial:functions-table-valued>`.

The SQL return type of the function may also be significant when executing a
statement and getting rows back, for those cases where SQLAlchemy has to apply
result-set processing. A prime example of this are date-related functions on
SQLite, where SQLAlchemy's {class}`~sqlalchemy.types.DateTime` and related datatypes take
on the role of converting from string values to Python `datetime()` objects
as result rows are received.

To apply a specific type to a function we're creating, we pass it using the
{paramref}`~sqlalchemy.sql.functions.Function.type_` parameter; the type argument may be
either a {class}`~sqlalchemy.types.TypeEngine` class or an instance.  In the example
below we pass the {class}`~sqlalchemy.types.JSON` class to generate the PostgreSQL
`json_object()` function, noting that the SQL return type will be of
type JSON:

```{code-cell} ipython3
from sqlalchemy import JSON
function_expr = func.json_object('{a, 1, b, "def", c, 3.5}', type_=JSON)
```

By creating our JSON function with the {class}`~sqlalchemy.types.JSON` datatype, the
SQL expression object takes on JSON-related features, such as that of accessing
elements:

```{code-cell} ipython3
stmt = select(function_expr["def"])
print(stmt)
```

### Built-in Functions Have Pre-Configured Return Types

For common aggregate functions like {class}`~sqlalchemy.sql.functions.count`,
{class}`~sqlalchemy.sql.functions.max`, {class}`~sqlalchemy.sql.functions.min` as well as a very small number
of date functions like {class}`~sqlalchemy.sql.functions.now` and string functions like
{class}`~sqlalchemy.sql.functions.concat`, the SQL return type is set up appropriately,
sometimes based on usage. The {class}`~sqlalchemy.sql.functions.max` function and similar
aggregate filtering functions will set up the SQL return type based on the
argument given:

```{code-cell} ipython3
m1 = func.max(Column("some_int", Integer))
m1.type
```

```{code-cell} ipython3
m2 = func.max(Column("some_str", String))
m2.type
```

Date and time functions typically correspond to SQL expressions described by
{class}`~sqlalchemy.types.DateTime`, {class}`~sqlalchemy.types.Date` or {class}`~sqlalchemy.types.Time`:

```{code-cell} ipython3
func.now().type
```

```{code-cell} ipython3
func.current_date().type
```

A known string function such as {class}`~sqlalchemy.sql.functions.concat`
will know that a SQL expression would be of type {class}`~sqlalchemy.types.String`:

```{code-cell} ipython3
func.concat("x", "y").type
```

However, for the vast majority of SQL functions, SQLAlchemy does not have them
explicitly present in its very small list of known functions.  For example,
while there is typically no issue using SQL functions `func.lower()`
and `func.upper()` to convert the casing of strings, SQLAlchemy doesn't
actually know about these functions, so they have a "null" SQL return type:

```{code-cell} ipython3
func.upper("lowercase").type
```

For simple functions like `upper` and `lower`, the issue is not usually
significant, as string values may be received from the database without any
special type handling on the SQLAlchemy side, and SQLAlchemy's type
coercion rules can often correctly guess intent as well; the Python `+`
operator for example will be correctly interpreted as the string concatenation
operator based on looking at both sides of the expression:

```{code-cell} ipython3
print(select(func.upper("lowercase") + " suffix"))
```

Overall, the scenario where the
{paramref}`~sqlalchemy.sql.functions.Function.type_` parameter is likely necessary is:

1. the function is not already a SQLAlchemy built-in function; this can be
   evidenced by creating the function and observing the {attr}`~sqlalchemy.sql.functions.Function.type`
   attribute, that is:

   ```python
   func.count().type
   Integer()
   ```

   vs.:

   ```python
   func.json_object('{"a", "b"}').type
   NullType()
   ```

2. Function-aware expression support is needed; this most typically refers to
   special operators related to datatypes such as {class}`~sqlalchemy.types.JSON` or
   {class}`~sqlalchemy.types.ARRAY`

3. Result value processing is needed, which may include types such as
   {class}`~sqlalchemy.types.DateTime`, {class}`~sqlalchemy.types.Boolean`, {class}`~sqlalchemy.types.Enum`,
   or again special datatypes such as {class}`~sqlalchemy.types.JSON`,
   {class}`~sqlalchemy.types.ARRAY`.

(sqlatutorial:window-functions)=

### Using Window Functions

A window function is a special use of a SQL aggregate function which calculates
the aggregate value over the rows being returned in a group as the individual
result rows are processed.  Whereas a function like `MAX()` will give you
the highest value of a column within a set of rows, using the same function
as a "window function" will given you the highest value for each row,
*as of that row*.

In SQL, window functions allow one to specify the rows over which the
function should be applied, a "partition" value which considers the window
over different sub-sets of rows, and an "order by" expression which importantly
indicates the order in which rows should be applied to the aggregate function.

In SQLAlchemy, all SQL functions generated by the {data}`~sqlalchemy.sql.expression.func` namespace
include a method {meth}`~sqlalchemy.sql.functions.FunctionElement.over` which
grants the window function, or "OVER", syntax; the construct produced
is the {class}`~sqlalchemy.sql.expression.Over` construct.

A common function used with window functions is the `row_number()` function
which simply counts rows. We may partition this row count against user name to
number the email addresses of individual users.

:::{note}
`ROW_NUMBER()` is only available in SQLite version 3.25 or newer.
:::

```{code-cell} ipython3
:tags: [raises-exception]

stmt = select(
    func.row_number().over(partition_by=user_table.c.name),
    user_table.c.name,
    address_table.c.email_address
).select_from(user_table).join(address_table)
with engine.connect() as conn:
    result = conn.execute(stmt)
    print(result.all())
```

Above, the {paramref}`~sqlalchemy.sql.functions.FunctionElement.over.partition_by` parameter
is used so that the `PARTITION BY` clause is rendered within the OVER clause.
We also may make use of the `ORDER BY` clause using {paramref}`~sqlalchemy.sql.functions.FunctionElement.over.order_by`:

```{code-cell} ipython3
stmt = select(
    func.count().over(order_by=user_table.c.name),
    user_table.c.name,
    address_table.c.email_address).select_from(user_table).join(address_table)
with engine.connect() as conn:
    result = conn.execute(stmt)
    print(result.all())
```

Further options for window functions include usage of ranges; see
{func}`~sqlalchemy.sql.expression.over` for more examples.

:::{tip}
It's important to note that the {meth}`~sqlalchemy.sql.functions.FunctionElement.over`
method only applies to those SQL functions which are in fact aggregate
functions; while the {class}`~sqlalchemy.sql.expression.Over` construct will happily render itself
for any SQL function given, the database will reject the expression if the
function itself is not a SQL aggregate function.
:::

(sqlatutorial:functions-within-group)=

### Special Modifiers WITHIN GROUP, FILTER

The "WITHIN GROUP" SQL syntax is used in conjunction with an "ordered set"
or a "hypothetical set" aggregate
function.  Common "ordered set" functions include `percentile_cont()`
and `rank()`.  SQLAlchemy includes built in implementations
{class}`~sqlalchemy.sql.functions.rank`, {class}`~sqlalchemy.sql.functions.dense_rank`,
{class}`~sqlalchemy.sql.functions.mode`, {class}`~sqlalchemy.sql.functions.percentile_cont` and
{class}`~sqlalchemy.sql.functions.percentile_disc` which include a {meth}`~sqlalchemy.sql.functions.FunctionElement.within_group`
method:

```{code-cell} ipython3
print(
    func.unnest(
        func.percentile_disc([0.25,0.5,0.75,1]).within_group(user_table.c.name)
    )
)
```

"FILTER" is supported by some backends to limit the range of an aggregate function to a
particular subset of rows compared to the total range of rows returned, available
using the {meth}`~sqlalchemy.sql.functions.FunctionElement.filter` method:

```{code-cell} ipython3
stmt = select(
    func.count(address_table.c.email_address).filter(user_table.c.name == 'sandy'),
    func.count(address_table.c.email_address).filter(user_table.c.name == 'spongebob')
).select_from(user_table).join(address_table)
with engine.connect() as conn:
    result = conn.execute(stmt)
    print(result.all())
```

(sqlatutorial:functions-table-valued)=

### Table-Valued Functions

Table-valued SQL functions support a scalar representation that contains named
sub-elements. Often used for JSON and ARRAY-oriented functions as well as
functions like `generate_series()`, the table-valued function is specified in
the FROM clause, and is then referred towards as a table, or sometimes even as
a column. Functions of this form are prominent within the PostgreSQL database,
however some forms of table valued functions are also supported by SQLite,
Oracle, and SQL Server.

:::{seealso}
{ref}`postgresql_table_valued_overview` - in the {ref}`postgresql_toplevel` documentation.

While many databases support table valued and other special
forms, PostgreSQL tends to be where there is the most demand for these
features.   See this section for additional examples of PostgreSQL
syntaxes as well as additional features.
:::

SQLAlchemy provides the {meth}`~sqlalchemy.sql.functions.FunctionElement.table_valued` method
as the basic "table valued function" construct, which will convert a
{data}`~sqlalchemy.sql.expression.func` object into a FROM clause containing a series of named
columns, based on string names passed positionally. This returns a
{class}`~sqlalchemy.sql.expression.TableValuedAlias` object, which is a function-enabled
{class}`~sqlalchemy.sql.expression.Alias` construct that may be used as any other FROM clause as
introduced at {ref}`sqlatutorial:using-aliases`. Below we illustrate the
`json_each()` function, which while common on PostgreSQL is also supported by
modern versions of SQLite:

```{code-cell} ipython3
onetwothree = func.json_each('["one", "two", "three"]').table_valued("value")
stmt = select(onetwothree).where(onetwothree.c.value.in_(["two", "three"]))
with engine.connect() as conn:
    result = conn.execute(stmt)
    print(result.all())
```

Above, we used the `json_each()` JSON function supported by SQLite and
PostgreSQL to generate a table valued expression with a single column referred
towards as `value`, and then selected two of its three rows.

:::{seealso}
{ref}`postgresql_table_valued` - in the {ref}`postgresql_toplevel` documentation -
this section will detail additional syntaxes such as special column derivations
and "WITH ORDINALITY" that are known to work with PostgreSQL.
:::

(sqlatutorial:functions-column-valued)=

### Column Valued Functions - Table Valued Function as a Scalar Column

A special syntax supported by PostgreSQL and Oracle is that of referring
towards a function in the FROM clause, which then delivers itself as a
single column in the columns clause of a SELECT statement or other column
expression context.  PostgreSQL makes great use of this syntax for such
functions as `json_array_elements()`, `json_object_keys()`,
`json_each_text()`, `json_each()`, etc.

SQLAlchemy refers to this as a "column valued" function and is available
by applying the {meth}`~sqlalchemy.sql.functions.FunctionElement.column_valued` modifier
to a {class}`~sqlalchemy.sql.functions.Function` construct:

```{code-cell} ipython3
from sqlalchemy import select, func
stmt = select(func.json_array_elements('["one", "two"]').column_valued("x"))
print(stmt)
```

The "column valued" form is also supported by the Oracle dialect, where
it is usable for custom SQL functions:

```{code-cell} ipython3
from sqlalchemy.dialects import oracle
stmt = select(func.scalar_strings(5).column_valued("s"))
print(stmt.compile(dialect=oracle.dialect()))
```

:::{seealso}
{ref}`postgresql_column_valued` - in the {ref}`postgresql_toplevel` documentation.
:::
