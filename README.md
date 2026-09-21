# remarkable-bujo

A reproducible hyperlinked Bullet Journal planner generator for reMarkable tablets.

The goal is to keep the Bullet Journal method while removing the physical page-count constraint: annual, monthly, weekly and daily views are generated as one navigable PDF.

## Current scope

The first version generates a 2027 planner with:

- year overview;
- six Future Log pages (two months per page);
- 12 monthly calendars;
- one dedicated Monthly Log page per month;
- ISO weekly overview pages;
- one Weekly Log / Reflection page per ISO week;
- one daily page per day;
- monthly reflection pages;
- an annual reflection page;
- project and collection index pages;
- internal PDF links for navigation;
- a minimal dot-grid daily layout suitable for handwriting.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Generate

```bash
remarkable-bujo --year 2027 --output bujo-2027.pdf
```

or:

```bash
python -m remarkable_bujo --year 2027 --output bujo-2027.pdf
```

## Design principles

- minimal interface;
- no forced productivity fields;
- no duplicated information;
- dates and navigation are generated automatically;
- source-controlled and reproducible;
- year-independent generator.

## License

GPL-3.0-or-later
