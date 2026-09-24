# dapt — Duke APT Helper

Command-line tool for checking, running, and submitting Duke CS201 APT solutions.

## Install

Requires Python 3.14+, [uv](https://docs.astral.sh/uv/), and Java for local execution.

From a checkout:

```sh
uv tool install .
```

For local development, use `uv tool install --editable .`

## Authenticate

Save an authenticated Duke APT browser session:

```sh
dapt auth
```

When prompted, paste the `Cookie` request-header value from an authenticated
`apt.cs.duke.edu` request in your browser's developer tools. The cookie is
stored locally in `~/.local/state/dapt/dapt.db`; treat it as a login
credential. Authentication immediately syncs submission results to verify the
new session. Run `dapt auth` again when it expires.

## Usage

```sh
dapt problems                        # list known APTs, details, and source mappings
dapt sync                            # fetch and cache latest submission results
dapt status                          # show cached results and file status
dapt status 1                        # show one APT set
dapt run gravity                    # run the expected Java file locally
dapt submit gravity                 # upload an APT
```

Run `dapt problems` to see valid APT names and details; names and class names are
case-insensitive. The expected source files are under `apts/`, for example
`apts/set1/Gravity.java`. Submission results are displayed by `sync` and
`submit`; `sync` retains only the latest result for each problem. The database
stores the browser cookie, latest status, last-sync timestamp, and uploaded-file
hashes used by `status`.

## Development

```sh
uv sync --locked --all-groups
uv run pytest
uv build
```
