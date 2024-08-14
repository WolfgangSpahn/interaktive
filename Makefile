# Include .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

help:           ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e "s/\\$$//" | sed -e "s/##//"

IMG_DIR = docs
FIND=find

# Convert paths to the correct format for Windows
ifeq ($(OS), Windows_NT)
    IMG_DIR := $(subst /,\\,$(IMG_DIR))
	FIND=gfind
endif

init:          	## Initialize the project.
	@npm init -y

install:        ## installs dependencies
	@npm install

build: install  ## Bundle js with rollup.
	@npm run build

render:	build   ## Render the project.
	@quarto render index.qmd

.PHONY: images
images: render        ## copy images to the docs folder
	cp -r images $(IMG_DIR)

test:		   ## run pytest
	cd backend && make test

serve:          ## Serves the project
	cd backend && make run

clean:          ## clean up
	rm -rf docs
	rm -rf node_modules
	gfind . -type f -name '*~' -delete
	cd backend && make clean

push:           ## push to github
	git push origin main

ssh_key: 	## make NEW ssh key
	ssh-keygen -t rsa -b 4096 -C "wolfgang.spahn@gmail.com"

ssh_gh_test:	## test github connection
	ssh -T git@github.com
