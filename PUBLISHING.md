# Publishing

## Integration releases

Repository: https://github.com/brylee123/ha-pseg-nj.

The CI workflow runs standalone and native HA tests. After a successful push
build on the current `main` commit, the release workflow reads the manifest
version, creates a matching `v` tag and publishes an experimental prerelease
with `pseg_nj.zip` and `SHA256SUMS`. Existing releases are left unchanged.
Bump the integration manifest version and update the release notes before the
next release. No personal token is needed: Actions uses its repository token.

## Standalone library

Distribution: `pseg-nj-mymeter`; import package: `pseg_mymeter`.
Version `0.2.0` is published on production PyPI under MIT by `brylee123`.
Do not upload that version again. Repository documentation changes do not alter
the already published artifacts.

For a future library release, follow the
[PyPA packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/):

1. Bump `library/pyproject.toml`, update library metadata and release notes.
2. Run standalone tests, lint and `scripts/check_runtime_dependency.py`.
3. Build with `python -m build library` and inspect with `python -m twine check --strict library/dist/*`.
4. Install the wheel in an isolated environment and check imports.
5. Upload the explicit reviewed filenames using Twine and an appropriately scoped PyPI token, or configure Trusted Publishing first.
6. Verify the published metadata, hashes, exact version and clean installation.
7. Update the integration's exact manifest requirement and run both test suites.

Keep tokens in a credential store, never in source, command arguments or chat.
PyPI filenames cannot be reused; code or metadata changes require a new version.
Automated PyPI publishing is not configured. Live portal/HAOS tests remain
separate from packaging and automated validation.
