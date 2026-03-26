# Quick Task 260326-qj9: Summary

**Date:** 2026-03-26
**Status:** Complete

## Changes Made

### homesearch/api/routes.py

1. **on_progress signature** (line 71): Added `found: int = 0` parameter so it matches the 4-arg call from search_service's `_wrapped_progress`.

2. **find_city ValueError** (line 241): Wrapped `search.find_city()` in `try/except ValueError` so unrecognized city names (e.g. 'Abbott') return an empty candidates list instead of crashing the autocomplete endpoint with a 500.

## Root Causes

- `uszipcode.SearchEngine.find_city()` raises `ValueError` for city names not in its database — the caller assumed it always returns a list.
- `search_service._wrapped_progress` calls `on_progress(current, total, location, found)` with 4 args, but the `stream_search` closure in routes.py only declared 3 parameters.
