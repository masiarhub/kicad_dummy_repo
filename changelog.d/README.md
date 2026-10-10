# Changelog fragments

Don't edit `CHANGELOG.md` on a feature branch. Add a **new** file here instead,
one per change, named `<feature>-<topic>.md` (e.g. `power-gen-buck.md`):

```markdown
### Added
- 5V buck converter (TPS62130), 3 A

### Fixed
- Swapped CAN_H / CAN_L labels
```

Headings: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
Every PR adds a different file, so PRs never conflict here. Don't edit or
delete other people's fragments.

The PR check validates the fragments. When a release tag is pushed, CI moves
all fragments into `CHANGELOG.md` (section of the new version) and deletes
them. Preview locally: `python3 .github/scripts/collect_changelog.py --check`.
