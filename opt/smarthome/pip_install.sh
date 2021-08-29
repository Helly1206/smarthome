#!/bin/bash
echo "Checking and installing required PIP packages"

PKG_OK=$(dpkg-query -W --showformat='${Status}\n' python3-pip|grep "install ok installed")
echo Checking for pip3: $PKG_OK
if [ "" == "$PKG_OK" ]; then
    echo "No pip3. Setting up pip3."
    sudo apt-get --force-yes --yes install python3-pip
fi

echo "Installing required python packages"
PKG_OK=$(sudo -H pip3 freeze| grep -i "Enum34==")
echo Checking for Enum: $PKG_OK
if [ "" == "$PKG_OK" ]; then
    echo "No Enum. Setting up Enum."
    sudo -H pip3 install enum34
fi
PKG_OK=$(sudo -H pip3 freeze| grep -i "Flask==")
echo Checking for Flask: $PKG_OK
if [ "" == "$PKG_OK" ]; then
    echo "No Flask. Setting up Flask."
    sudo -H pip3 install flask
fi
PKG_OK=$(sudo -H pip3 freeze| grep -i "psutil==")
echo Checking for psutil: $PKG_OK
if [ "" == "$PKG_OK" ]; then
    echo "No psutil. Setting up psutil."
    sudo -H pip3 install psutil
fi
PKG_OK=$(sudo -H pip3 freeze| grep -i "ifaddr==")
echo Checking for ifaddr: $PKG_OK
if [ "" == "$PKG_OK" ]; then
    echo "No ifaddr. Setting up ifaddr."
    sudo -H pip3 install ifaddr
fi

echo "Ready"
