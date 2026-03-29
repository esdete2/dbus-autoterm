.PHONY: package deploy package\:native-gui deploy\:native-gui

package:
	sh ./scripts/package-dbus-autoterm.sh

deploy: package
	sh ./scripts/deploy-dbus-autoterm.sh

package\:native-gui:
	GUI_VARIANT=native-gui sh ./scripts/package-dbus-autoterm.sh

deploy\:native-gui:
	$(MAKE) package:native-gui
	GUI_VARIANT=native-gui sh ./scripts/deploy-dbus-autoterm.sh
