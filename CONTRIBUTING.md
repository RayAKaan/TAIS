# Contributing to TAIS

Thank you for contributing.

## Development setup

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run tests

```bash
make test
```

## Contribution areas

- New DSL domains
- New experiment suites
- Visualization improvements
- Statistical baselines
- Documentation
- Swarm V6 extensions

## Adding a domain

See [`docs/domain-guide.md`](docs/domain-guide.md).

## Adding an experiment

See [`docs/experiment-guide.md`](docs/experiment-guide.md).

## Requirements

- Keep `UniversalMote` domain-agnostic.
- Do not add domain-specific logic to `UniversalMote`.
- Add tests for new behavior.
- Preserve reproducibility.
- Report negative results honestly.

## Pull request checklist

- [ ] Tests pass
- [ ] New functionality has tests
- [ ] Docs updated if needed
- [ ] Results include seeds / parameters
- [ ] No generated junk committed unless curated
