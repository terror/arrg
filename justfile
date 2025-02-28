set dotenv-load

export EDITOR := 'nvim'

alias c := check
alias f := fmt
alias t := test

default:
  just --list

all: fmt check readme

build:
  uv build

dev-deps:
  cargo install present tokei typos

check:
  uv run ruff check

count:
  tokei src

fmt:
   ruff check --select I --fix && ruff format

publish:
  rm -rf dist && uv build && uv publish

readme:
  present --in-place README.md && typos --write-changes README.md

test *args:
  uv run pytest --verbose {{args}}
