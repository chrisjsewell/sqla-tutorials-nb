---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
sd_hide_title: true
---

(unified-tutorial)=

# SQLAlchemy 1.4 / 2.0 Tutorial

::::{grid} 1
:::{grid-item}
```{image} ./_static/logo-long.png
:width: 400px
:class: sd-m-auto
```
:::
:::{grid-item}
:class: sd-fs-3 sd-text-center sd-font-weight-bold

Notebook based 1.4 / 2.0 Tutorial
:::
::::

:::{admonition} About this document

This tutorial is a mirror of <https://github.com/sqlalchemy/sqlalchemy/tree/master/doc/build/tutorial>,
converted to use Jupyter Notebooks for interactive exploration.
Use the {octicon}`rocket` dropdown at the top of the page to launch interactive sessions.

The new SQLAlchemy Tutorial is now integrated between Core and ORM and
serves as a unified introduction to SQLAlchemy as a whole.   In the new
{term}`2.0 style` of working, fully available in the {ref}`1.4 release <migration_14_toplevel>`, the ORM now uses Core-style querying with the
{func}`~sqlalchemy.future.select` construct, and transactional semantics between Core
connections and ORM sessions are equivalent.   Take note of the blue
border styles for each section, that will tell you how "ORM-ish" a
particular topic is!

Users who are already familiar with SQLAlchemy, and especially those
looking to migrate existing applications to work under SQLAlchemy 2.0
within the 1.4 transitional phase should check out the
{ref}`migration_20_toplevel` document as well.

For the newcomer, this document has a **lot** of detail, however by the
end they will be considered an **Alchemist**.
:::

SQLAlchemy is presented as two distinct APIs, one building on top of the other.
These APIs are known as **Core** and **ORM**.

:::{div} core-header

**SQLAlchemy Core** is the foundational architecture for SQLAlchemy as a
"database toolkit".  The library provides tools for managing connectivity
to a database, interacting with database queries and results, and
programmatic construction of SQL statements.

Sections that have a **dark blue border on the right** will discuss
concepts that are **primarily Core-only**; when using the ORM, these
concepts are still in play but are less often explicit in user code.
:::

:::{div} orm-header

**SQLAlchemy ORM** builds upon the Core to provide optional **object
relational mapping** capabilities.   The ORM provides an additional
configuration layer allowing user-defined Python classes to be **mapped**
to database tables and other constructs, as well as an object persistence
mechanism known as the **Session**.   It then extends the Core-level
SQL Expression Language to allow SQL queries to be composed and invoked
in terms of user-defined objects.

Sections that have a **light blue border on the left** will discuss
concepts that are **primarily ORM-only**.  Core-only users
can skip these.
:::

:::{div} core-header, orm-dependency

A section that has **both light and dark borders on both sides** will
discuss a **Core concept that is also used explicitly with the ORM**.
:::

## Tutorial Overview

The tutorial will present both concepts in the natural order that they
should be learned, first with a mostly-Core-centric approach and then
spanning out into more ORM-centric concepts.

The major sections of this tutorial are as follows:

```{toctree}
:hidden: true
:maxdepth: 10

engine
dbapi_transactions
metadata
data
orm_data_manipulation
orm_related_objects
further_reading
```

- {ref}`sqlatutorial:engine` - all SQLAlchemy applications start with an
  {class}`~sqlalchemy.future.Engine` object; here's how to create one.
- {ref}`sqlatutorial:working-with-transactions` - the usage API of the
  {class}`~sqlalchemy.future.Engine` and it's related objects {class}`~sqlalchemy.future.Connection`
  and {class}`~sqlalchemy.engine.Result` are presented here. This content is Core-centric
  however ORM users will want to be familiar with at least the
  {class}`~sqlalchemy.engine.Result` object.
- {ref}`sqlatutorial:working-with-metadata` - SQLAlchemy's SQL abstractions as well
  as the ORM rely upon a system of defining database schema constructs as
  Python objects.   This section introduces how to do that from both a Core and
  an ORM perspective.
- {ref}`sqlatutorial:working-with-data` - here we learn how to create, select,
  update and delete data in the database.   The so-called {term}`CRUD`
  operations here are given in terms of SQLAlchemy Core with links out towards
  their ORM counterparts.  The SELECT operation that is introduced in detail at
  {ref}`sqlatutorial:selecting-data` applies equally well to Core and ORM.
- {ref}`sqlatutorial:orm-data-manipulation` covers the persistence framework of the
  ORM; basically the ORM-centric ways to insert, update and delete, as well as
  how to handle transactions.
- {ref}`sqlatutorial:orm-related-objects` introduces the concept of the
  {func}`~sqlalchemy.orm.relationship` construct and provides a brief overview
  of how it's used, with links to deeper documentation.
- {ref}`sqlatutorial:further-reading` lists a series of major top-level
  documentation sections which fully document the concepts introduced in this
  tutorial.

<!--
.. rst-class:: core-header, orm-dependency
-->

### Version Check

If running the examples, it is advised that the reader performs a quick check to
verify that we are on  **version 1.4** of SQLAlchemy.
The SQLite version should also preferably by [version 3.25](https://www.sqlite.org/releaselog/3_25_0.html) or higher.

```{code-cell} ipython3
import sqlalchemy
import sqlite3

print(sqlalchemy.__version__)
print(sqlite3.sqlite_version)
```

<!--
.. rst-class:: core-header, orm-dependency
-->

### A Note on the Future

This tutorial describes a new API that's released in SQLAlchemy 1.4 known
as {term}`2.0 style`.   The purpose of the 2.0-style API is to provide forwards
compatibility with {ref}`SQLAlchemy 2.0 <migration_20_toplevel>`, which is
planned as the next generation of SQLAlchemy.

In order to provide the full 2.0 API, a new flag called `future` will be
used, which will be seen as the tutorial describes the {class}`~sqlalchemy.future.Engine`
and {class}`~sqlalchemy.orm.Session` objects.   These flags fully enable 2.0-compatibility
mode and allow the code in the tutorial to proceed fully.  When using the
`future` flag with the {func}`~sqlalchemy.future.create_engine` function, the object
returned is a sublass of {class}`~sqlalchemy.future.Engine` described as
{class}`~sqlalchemy.future.Engine`. This tutorial will be referring to
{class}`~sqlalchemy.future.Engine`.
