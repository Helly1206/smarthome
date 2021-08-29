#!/bin/bash
INSTALL="/usr/bin/install -c"
INSTALL_DATA="$INSTALL -m 644"
INSTALL_PROGRAM="$INSTALL"
INSTALL_FOLDER="cp -r"
NAME="smarthome"
WEBNAME="gsh"
APPSNAME="gshApps"
PASSWDNAME="WebPassword"
WEBSTARTER="$WEBNAME""WebStarter"
ETCDIR="/etc"
ETCLOC="$ETCDIR/$NAME"
XML_NAME="$NAME.xml"
XML_DEVNAME="$NAME""Devices.xml"
XML_DOMONAME="$NAME""Domotion.xml"
OPTDIR="/opt"
OPTLOC="$OPTDIR/$NAME"
SYSTEMDDIR="./systemd"
SERVICEDIR="$ETCDIR/systemd/system"
SERVICESCRIPT="$NAME.service"
WEBSERVICESCRIPT="$WEBNAME.service"
PIP_INSTALL="$OPTLOC/pip_install.sh"
DEBFOLDER="debian"

if [ "$EUID" -ne 0 ]
then
	echo "Please execute as root ('sudo install.sh')"
	exit
fi

if [ "$1" == "-u" ] || [ "$1" == "-U" ]
then
	echo "$NAME uninstall script"

	echo "Uninstalling daemon $NAME"
	systemctl stop "$SERVICESCRIPT"
	systemctl disable "$SERVICESCRIPT"
	if [ -e "$SERVICEDIR/$SERVICESCRIPT" ]; then rm -f "$SERVICEDIR/$SERVICESCRIPT"; fi

	echo "Uninstalling daemon $WEBNAME"
	systemctl stop "$WEBSERVICESCRIPT"
	systemctl disable "$WEBSERVICESCRIPT"
	if [ -e "$SERVICEDIR/$WEBSERVICESCRIPT" ]; then rm -f "$SERVICEDIR/$WEBSERVICESCRIPT"; fi

	echo "Uninstalling $NAME"
	if [ -d "$OPTLOC" ]; then rm -rf "$OPTLOC"; fi
elif [ "$1" == "-h" ] || [ "$1" == "-H" ]
then
	echo "Usage:"
	echo "  <no argument>: install gsh smarthome"
	echo "  -u/ -U       : uninstall gsh smarthome"
	echo "  -h/ -H       : this help file"
    echo "  -d/ -D       : build debian package"
	echo "  -c/ -C       : Cleanup compiled files in install folder"
    echo ""
    echo "Apache2 install is removed from this install script"
    echo "To install apach2 web deployment, run /opt/smarthome/apache2_install.sh"
elif [ "$1" == "-c" ] || [ "$1" == "-C" ]
then
	echo "$NAME Deleting compiled files in install folder"
	py3clean .
    rm -f ./*.deb
	rm -rf "$DEBFOLDER"/${NAME,,}
	rm -rf "$DEBFOLDER"/.debhelper
	rm -f "$DEBFOLDER"/files
	rm -f "$DEBFOLDER"/files.new
	rm -f "$DEBFOLDER"/${NAME,,}.*
elif [ "$1" == "-d" ] || [ "$1" == "-D" ]
then
	echo "$NAME build debian package"
	py3clean .
	fakeroot debian/rules clean binary
	mv ../*.deb .
else
	echo "$NAME install script"

	echo "Stop running services"
	systemctl stop $SERVICESCRIPT
	systemctl disable $SERVICESCRIPT
	systemctl stop $WEBSERVICESCRIPT
	systemctl disable $WEBSERVICESCRIPT

	echo "Installing $NAME"

	py3clean .

	if [ -d "$OPTLOC" ]; then rm -rf "$OPTLOC"; fi
	if [ ! -d "$OPTLOC" ]; then
		mkdir "$OPTLOC"
		chmod 755 "$OPTLOC"
	fi

	$INSTALL_FOLDER ".$OPTLOC/*" $OPTLOC
	$INSTALL_PROGRAM ".$OPTLOC/$WEBSTARTER" $OPTLOC
	$INSTALL_PROGRAM ".$OPTLOC/$APPSNAME" $OPTLOC
	$INSTALL_PROGRAM ".$OPTLOC/$PASSWDNAME" $OPTLOC
	$INSTALL_PROGRAM ".$OPTLOC/$A2CONFIG" $OPTLOC
	$INSTALL_PROGRAM ".$OPTLOC/${0##*/}" $OPTLOC

	echo "Installing $ETCLOC"
	if [ ! -d "$ETCLOC" ]; then
		mkdir "$ETCLOC"
		chmod 755 "$ETCLOC"
	fi

	echo "Installing $XML_NAME"
	if [ ! -e "$ETCLOC/$XML_NAME" ]; then
		$INSTALL_DATA ".$ETCLOC/$XML_NAME" "$ETCLOC/$XML_NAME"
	fi

    echo "Installing $XML_DEVNAME"
    if [ ! -e "$ETCLOC/$XML_DEVNAME" ]; then
        $INSTALL_DATA ".$ETCLOC/$XML_DEVNAME" "$ETCLOC/$XML_DEVNAME"
    fi

    echo "Installing $XML_DOMONAME"
    if [ ! -e "$ETCLOC/$XML_DOMONAME" ]; then
        $INSTALL_DATA ".$ETCLOC/$XML_DOMONAME" "$ETCLOC/$XML_DOMONAME"
    fi

    py3clean "$OPTLOC"

    source "$PIP_INSTALL"

	echo "Installing daemon $NAME"
	read -p "Do you want to install an automatic startup service for $NAME (Y/n)? " -n 1 -r
	echo    # (optional) move to a new line
	if [[ $REPLY =~ ^[Nn]$ ]]
	then
		echo "Skipping install automatic startup service for $NAME"
	else
		echo "Install automatic startup service for $NAME"
		$INSTALL_DATA ".$SERVICEDIR/$SERVICESCRIPT" "$SERVICEDIR/$SERVICESCRIPT"

		systemctl enable $SERVICESCRIPT
		systemctl start $SERVICESCRIPT
	fi

	echo "Installing daemon $WEBNAME"
	read -p "Do you want to install an automatic startup service for $WEBNAME (Y/n)? " -n 1 -r
	echo    # (optional) move to a new line
	if [[ $REPLY =~ ^[Nn]$ ]]
	then
		echo "Skipping install automatic startup service for $WEBNAME"
	else
		echo "Install automatic startup service for $WEBNAME"
		$INSTALL_DATA ".$SERVICEDIR/$WEBSERVICESCRIPT" "$SERVICEDIR/$WEBSERVICESCRIPT"

		systemctl enable $WEBSERVICESCRIPT
		systemctl start $WEBSERVICESCRIPT
	fi
fi
