Run the project's linting and testing tools to check code quality.

Run the following checks in order, fixing issues as you go:

1. **ruff format** - Auto-format code
   ```
   ruff format quodlibet tests
   ```

2. **ruff check** - Lint check (auto-fix safe issues)
   ```
   ruff check --fix quodlibet tests
   ```

3. **mypy** - Type checking
   ```
   mypy quodlibet tests
   ```

If the user provides specific file paths, scope all commands to those files only. Otherwise run against the full `quodlibet` and `tests` directories.

After running each tool:
- Summarize the results concisely
- Fix any auto-fixable issues
- For remaining errors, group by category and suggest fixes
- If mypy has many pre-existing errors, focus only on errors in files that were recently changed (check `git diff --name-only` against the main branch)

For running the test suite specifically:
```
pytest tests/ -x --tb=short
```

Use `-x` to stop on first failure for faster iteration. Use `-k pattern` to run specific test subsets.
