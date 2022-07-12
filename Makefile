.PHONY: package
package:  ## Build rpm packages
	tito build --test --rpm --rpmbuild-options='-ba --nocheck --without tests' -o .

.PHONY: clean
clean: ## Clean all make artifacts
	rm -rf rpmbuild
