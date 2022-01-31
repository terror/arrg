set dotenv-load

export EDITOR := 'nvim'

alias f := fmt

default:
  just --list

fmt:
	yapf --in-place --recursive .
