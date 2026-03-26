.PHONY: package deploy

package:
	./scripts/package-dbus-autoterm.sh

deploy: package
	./scripts/deploy-dbus-autoterm.sh
