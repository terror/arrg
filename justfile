set dotenv-load

export EDITOR := 'nvim'

alias f := fmt
alias t := test

default:
  just --list

build:
	python3 setup.py sdist && python3 setup.py build

clean:
	rm -rf dist build *.egg-info

edit:
	pipenv install -e .

fmt:
	yapf --in-place --recursive .

lock:
	pipenv lock --pre

publish:
	twine upload dist/*

test:
	pytest
