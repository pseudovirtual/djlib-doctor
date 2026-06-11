## Summary

What changed?

## Safety

- [ ] This change is read-only.
- [ ] This change uses synthetic fixtures only.
- [ ] This change does not write to a Rekordbox database.
- [ ] This change does not modify, move, convert, quarantine, or delete music files.

If any box is unchecked, explain why.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Docs

- [ ] User-visible behavior is documented.
- [ ] No docs update needed.
