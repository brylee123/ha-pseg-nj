# Publishing the standalone library

Distribution: `pseg-nj-mymeter`; import package: `pseg_mymeter`.
Initial public version: `0.2.0`. Author: `brylee123`. License: MIT.

The workflow follows the [PyPA packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

1. Run the local suite and library/vendor checks.
2. Build a wheel and source distribution with `python -m build library`.
3. Run `python -m twine check --strict library/dist/*`.
4. Install the wheel in an isolated environment and check imports.
5. Authenticate using a PyPI API token or configure Trusted Publishing.
6. Upload the exact reviewed files:

```text
python -m twine upload --non-interactive --username __token__ --repository-url https://upload.pypi.org/legacy/ library/dist/pseg_nj_mymeter-0.2.0-py3-none-any.whl library/dist/pseg_nj_mymeter-0.2.0.tar.gz
```

For this local release, the reviewed distributions are in the workspace's
`outputs/library-dist/` instead of `library/dist/`; use those explicit filenames.
On Windows, `python -m keyring set https://upload.pypi.org/legacy/ __token__`
prompts privately and stores the token in Windows Credential Manager. Twine
retrieves it without putting it in command arguments, source files or chat.

The first upload requires a token scoped to the account because the project
does not yet exist. A public repository, issue tracker, tagged releases and
automated publishing still need setup before using this as a Home Assistant
Core dependency. TestPyPI is a separate service/account; this release request
targets production PyPI. Local validation does not claim live PSE&G/HA testing.

After upload, verify project metadata and both files on PyPI, install from the
index in a clean environment and check the exact version. Release filenames
cannot be reused: any later code/metadata change needs a new version.
