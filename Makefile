.PHONY: package
package:  ## Build rpm packages
	tito build --test --rpm

.PHONY: clean
clean: ## Clean all make artifacts
	rm -rf rpmbuild
