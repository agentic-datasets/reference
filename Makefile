# Documentation build and publish. The suite itself is run with pytest and the
# conformance CLI; this file is only about the docs site.
#
# The chapters are generated from the repository's own files -- CI fails if the
# two drift -- so `docs` regenerates before building rather than after.

EDGE        ?= root@172.105.24.72
REMOTE_ROOT ?= /var/www/agenticdatasets/reference
BOOK        ?= docs-site/book
RSYNC_FLAGS := -az --delete --chmod=D755,F644 --exclude .git --exclude .keep

PYTHON ?= python3

.PHONY: help docs deploy deploy-dry drift clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

docs: ## Regenerate the chapters and build the book
	$(PYTHON) docs-site/build.py
	mdbook build docs-site

drift: ## Fail if the committed chapters do not match what build.py produces
	$(PYTHON) docs-site/build.py
	git diff --exit-code docs-site/src

deploy: docs ## Publish the docs to agenticdatasets.org/reference/
	@test -f $(BOOK)/index.html || { echo "refusing: no $(BOOK)/index.html" >&2; exit 1; }
	rsync $(RSYNC_FLAGS) $(BOOK)/ $(EDGE):$(REMOTE_ROOT)/
	@echo "→ https://agenticdatasets.org/reference/"

deploy-dry: docs ## Show what deploy would change, without changing it
	rsync -n -v $(RSYNC_FLAGS) $(BOOK)/ $(EDGE):$(REMOTE_ROOT)/

clean: ## Remove the built book
	rm -rf $(BOOK)
