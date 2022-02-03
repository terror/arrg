set dotenv-load

export EDITOR := 'nvim'

alias f := fmt
alias t := test

default:
  just --list

edit:
	pipenv install -e .

fmt:
	yapf --in-place --recursive .

test:
	pytest
