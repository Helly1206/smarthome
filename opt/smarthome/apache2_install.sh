#!/bin/bash
NAME="smarthome"
WEBNAME="gsh"
WEBSTARTER="$WEBNAME""WebStarter"
OPTDIR="/opt"
OPTLOC="$OPTDIR/$NAME"
WEB_ROOT="/var/www"
GSHWEB_ROOT="$WEB_ROOT/$NAME"
WEBLOC="$OPTLOC/webif"
INSTALL_WEB="cp -r $WEBLOC/*"
A2CONFIG="$OPTLOC/Apache2Config"

if [ "$EUID" -ne 0 ]
then
	echo "Please execute as root ('sudo install.sh')"
	exit
fi

if [ "$1" == "-u" ] || [ "$1" == "-U" ]
then
    echo "$NAME Apache2 uninstall script"
	echo "WARNING: Apache2 itself is not uninstalled, evenso conf files are not removed"
	echo "    If you want to do so, remove all externaldeployment entries"
	echo "    in /etc/smarthome/smarthome.xml and run sudo /opt/smarthome/apache2_install.sh"
	echo "    This uninstaller only removes smarthome files from apache's www folder"
	read -p "Do you want to continue (Y/n)? " -n 1 -r
	echo    # (optional) move to a new line
	if [[ $REPLY =~ ^[Nn]$ ]]
	then
		echo "Skipping Apache2 uninstall script"
	else
		echo "Running Apache2 uninstall script"
		echo "Uninstalling $NAME from $WEB_ROOT"

		if [ -d "$DOMOWEB_ROOT" ]; then rm -rf "$DOMOWEB_ROOT"; fi
	fi
elif [ "$1" == "-f" ] || [ "$1" == "-F" ]
then
    echo "$NAME Apache2 uninstall script (forced)"
	echo "WARNING: Apache2 itself is not uninstalled, evenso conf files are not removed"
	echo "    If you want to do so, remove all externaldeployment entries"
	echo "    in /etc/smarthome/smarthome.xml and run sudo /opt/smarthome/apache2_install.sh"
	echo "    This uninstaller only removes smarthome files from apache's www folder"
	echo "Running Apache2 uninstall script"
	echo "Uninstalling $NAME from $WEB_ROOT"

	if [ -d "$DOMOWEB_ROOT" ]; then rm -rf "$DOMOWEB_ROOT"; fi
elif [ "$1" == "-h" ] || [ "$1" == "-H" ]
then
	echo "Usage:"
	echo "  <no argument>: install Apache2 WSGI web deployment"
	echo "  -u/ -U       : uninstall Apache2 WSGI web deployment"
    echo "  -f/ -F       : uninstall Apache2 WSGI web deployment (forced)"
	echo "  -h/ -H       : this help file"

else
	echo "$NAME Apache2 install script"
	echo "Take care that you open the required ports when running ufw or another firewall"

	echo "Check required packages"

	PKG_OK=$(dpkg-query -W --showformat='${Status}\n' apache2|grep "install ok installed")
	echo Checking for apache2: $PKG_OK
	if [ "" == "$PKG_OK" ]; then
		echo "No apache2. Setting up apache2."
		sudo apt-get --force-yes --yes install apache2
	fi

	PKG_OK=$(dpkg-query -W --showformat='${Status}\n' libapache2-mod-wsgi-py3|grep "install ok installed")
	echo Checking for libapache2-mod-wsgi-py3: $PKG_OK
	if [ "" == "$PKG_OK" ]; then
		echo "No libapache2-mod-wsgi-py3. Setting up libapache2-mod-wsgi-py3."
		sudo apt-get --force-yes --yes install libapache2-mod-wsgi-py3
	fi

	echo "Enabling wsgi and ssl modules"
	a2enmod wsgi &> /dev/null
	a2enmod ssl &> /dev/null

	echo "Installing $NAME on $WEB_ROOT"
	if [ -d "$GSHWEB_ROOT" ]; then rm -rf "$GSHWEB_ROOT"; fi
	if [ ! -d "$GSHWEB_ROOT" ]; then
		mkdir "$GSHWEB_ROOT"
	fi

	$INSTALL_WEB "$GSHWEB_ROOT"

	echo "Configuring Apache2"
	$A2CONFIG
fi
