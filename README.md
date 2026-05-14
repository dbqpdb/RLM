# The RLM project

RLM (Random Legal Move) is a random, silly, irreverent, impatient, etc. chess-playing, er... "engine"?

It is not trying to be Stockfish. It picks moves at random from the legal move list, makes them, and occasionally has things to say about it. Originally written in Perl (`rlm.pl`), since translated to Python (`rlm.py`).

## Installation

The project uses a conda environment defined in `environment.yml`:

```sh
conda env create -f environment.yml
conda activate rlm
```

The dependency footprint is heavier than the project really needs — see [#39](https://github.com/dbqpdb/RLM/issues/39) for the plan to trim it down.

## Playing a game

```sh
python rlm.py
```

You'll be prompted on whether to play and which side to take. RLM plays the other side. Moves are entered in algebraic notation; the parser accepts a fairly wide range of forms (see [#15](https://github.com/dbqpdb/RLM/issues/15) for what's still being firmed up).

## Running tests

```sh
pytest
```

(See [#23](https://github.com/dbqpdb/RLM/issues/23) for the pytest migration — once that's in, the in-tree `TestRLM` runner is deprecated.)

## Contributing

- The `master` branch is protected. All changes land via pull request and require at least one approving review.
- CI runs pytest on PRs to `master`, and `flake8` (advisory) on every push and PR. See [#43](https://github.com/dbqpdb/RLM/issues/43) and [#44](https://github.com/dbqpdb/RLM/issues/44).
- Existing issues tagged `Small` or `good first issue` are reasonable starting points.
- PEP 8 compliance is a work in progress — see [#45](https://github.com/dbqpdb/RLM/issues/45). Lint will stay advisory until the codebase is clean, then flip to blocking.

## Roadmap

Tracked in [issues](https://github.com/dbqpdb/RLM/issues). A few highlights:

- Modularize the single-file `rlm.py` ([#38](https://github.com/dbqpdb/RLM/issues/38)).
- Settle on one coordinate convention ([#37](https://github.com/dbqpdb/RLM/issues/37)).
- Stronger move parsing and capture validation ([#15](https://github.com/dbqpdb/RLM/issues/15), [#10](https://github.com/dbqpdb/RLM/issues/10)).
- ASCII-art splash screen ([#18](https://github.com/dbqpdb/RLM/issues/18)).
- Live web / app architectures ([#20](https://github.com/dbqpdb/RLM/issues/20)).

## Non-goals

- **Playing well.** RLM picks uniformly at random from legal moves. Position evaluation work ([#22](https://github.com/dbqpdb/RLM/issues/22)) is for analysis and commentary, not for choosing moves.
- **Silently.** The `Loudmouth` class exists. It is not yet wired into gameplay (see [#19](https://github.com/dbqpdb/RLM/issues/19)), but it will be.
