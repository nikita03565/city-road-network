SHELL := /bin/bash

.PHONY: format
format:
	black .
	isort .