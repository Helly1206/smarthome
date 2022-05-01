gsh - smarthome v0.95

GSH - Google smarthome multiplexer
=== = ====== ========= ===========

This piece of software brings smarthome commands to the local system. It makes it possible to operate e.g. Domotion by google assistant,
but also apps can be made to talk with other 3rd party devices.

Installation:
-------------
- Browse to: https://github.com/Helly1206/smarthome
- Click the 'Clone or Download' button
- Click 'Download Zip'
- Unzip the zip file to a temporary location
- Open a terminal at this location
- Enter: 'sudo ./install.sh'
- Wait and answer the questions:
	Do you want to install an automatic startup service for gshApps (Y/n)?
   		Default = Y
   		If you want to automatically start gshApps during startup (or don't know), answer Y to this question.
   		If you do not want to install an automatic startup script, answer N to this question.
   	Do you want to install an automatic startup service for gsh Web Server (Y/n)?
   		Default = Y
   		If you want to automatically start gsh Web Server during startup (or don't know), answer Y to this question.
   		If you do not want to install an automatic startup script, answer N to this question.

Manually run gshApps:
-------- --- ---------
When you didn't install an automatic startup service for gshApps
- Run by /opt/smarthome/gshApps

No command line options available

gsh webserver:
-------- -------------
Configure your webserver in /etc/smarthome/smarthome.xml.
Example:
<smarthome>
	<webprefix/>
	<webhookdirect>/webhook</webhookdirect>
	<googleclientid>GOOGLECLIENTID</googleclientid>
	<googleclientsecret>GOOGLECLIENTSECRET</googleclientsecret>
	<googleapikey>GOOGLEAPIKEY</googleapikey>
	<username>me</username>
	<password>AHASHEDPASSWORD</password>
	<debuglog>false</debuglog>
	<webserver>
		<ssl>true</ssl>
		<port>4043</port>
		<certificate>/etc/letsencrypt/live/example.com/fullchain.pem</certificate>
		<privatekey>/etc/letsencrypt/live/example.com/privkey.pem</privatekey>
		<externaldeployment>true</externaldeployment>
		<serveradmin>admin@localhost</serveradmin>
		<servername>www.example.com</servername>
	</webserver>
</smarthome>

When not using external deployment, please enter:
sudo systemctl restart gshWeb.service

Manually starting the webserver:
-------- -------- --- -------------
When you didn't install an automatic startup service for gsh Web Server
- Run by /opt/smarthome/gshWebStarter

Usage for special options:
         gshWebStarter <args>
         -h, --help: this help file
         -d, --debug: start in debug mode on port 5000

External deployment of webserver by Apache2:
-------- ---------- -- --------- -- --------
Exernal deployment can be used to deploy the webserver on an external server like Apache2. A wsgi file is added for that purpose. When you like to use the Domotion webserver(s) for other purposes than testing, running on an Apache2 server is recommended. To make deploying of the webserver(s) by apache2 easier, an installation program is written, so you don't have to find out everything yourself. This installation program also is capable to add 'default' http and https servers. If you want to do special things, you do have to read the docs of Apache2 or a different webserver.

If you would like to use external deployment by Apache2:
- First make <externaldeployment> true for the required sites in /etc/smarthome/smarthome.xml and take care that all the other fields are correctly filled in (e.g. when using ssl, make the servername equal to the website host).
- Enter: 'sudo ./apache2_install.sh'
- The webserver(s) are now installed in Apache2 and enabled. Take care that you open the required ports in the firewall when accessing from another computer.

Take care that if you have a different application running on the same port (e.g. Domotion on 443), install this application first.

Apps:
-----
For the moment, only one app is implemented, but more to follow:
Domotion (with limited functionality)

Installer options:
--------- --------
sudo ./install.sh    --> Installs gsh
sudo ./install.sh -u --> Uninstalls gsh
sudo ./install.sh -c --> Deletes compiled files in install folder (only required when copying or zipping the install folder)

sudo /opt/smarthome/apache2_install.sh --> Install Apache2 and/ or configures Apache2 with the gsh Webserver
sudo /opt/smarthome/apache2_install.sh -u --> Removes the gsh Webserver form the Apache2 folder, it doesn't uninstall Apache2, neither removes entries. Remove the entries in /etc/smarthome/smarthome.xml and run sudo /opt/smarthome/apache2_install.sh to remove the entries first, before running sudo opt/smarthome/apache2_install.sh -u

Package install:
------- --------
Gsh installs automatically from deb package/ apt repository (only for debian based distros like debian or ubuntu).
If external deployment is set true in at least one of the entries in /etc/smarthome.xml, then the apache2 installer is executed automatically.
After changing smarthome.xml, /opt/smarthome/apache2_install.sh needs to be executed manually.

Security:
---------
CAUTION: gsh is as safe and secure as your system is.

Configuration:
--------------
In /etc/smarthome, 3 configuration files are found.
- smarthome.xml to configure the server
- smarthomeDevices.xml to add and configure devices
- smarthomeDomotion.xml to configure communication with Domotion using bda

Server configuration:
------ --------------
(More detailed version to come)
Use the Actions on Google Console to add a new project with a name of your choosing and click - Create Project.

Click Home Control, then click Smart Home.
On the left navigation menu under SETUP, click on Invocation.
Add your App's name. Click Save.
Click Save.
Add Credentials

Navigate to the Google Cloud Console API Manager for your project id.
Click 'Create credentials'
Click 'OAuth client ID'
Choose 'other'
Add name e.g. 'GOOGLECLIENTID'
Copy the client ID shown and insert it in <googleclientid> in smarthome.xml
Copy the client secret shown and insert it in <googleclientsecret> in smarthome.xml
Add Request Sync

The Request Sync feature allows a cloud integration to send a request to the Home Graph to send a new SYNC request.

Navigate to the Google Cloud Console API Manager for your project id.
Enable the HomeGraph API. This will be used to request a new sync and to report the state back to the HomeGraph.
Click Credentials
Click 'Create credentials'
Click 'API key'
Copy the API key shown and insert it in <googleapikey> in smarthome.xml
Navigate back to the Actions on Google Console.

On the left navigation menu under BUILD, click on Actions. Click on Add Your First Action and choose your app's language(s). Enter the URL for fulfillment, e.g. https://[YOUR REVERSE PROXY URL]/smarthome/ (don't forget trailing slash!!!), click Done.
On the left navigation menu under ADVANCED OPTIONS, click on Account Linking.
Select No, I only want to allow account creation on my website. Click Next.
For Linking Type, select OAuth.
For Grant Type, select 'Authorization Code' for Grant Type.
Under Client Information, enter the client ID and secret from earlier.
Change Authorization URL to https://[YOUR REVERSE PROXY URL]/oauth (replace with your actual URL).
Change Token URL to https://[YOUR REVERSE PROXY URL]/token (replace with your actual URL). In the Configure your client section:
Do NOT check Google to transmit clientID and secret via HTTP basic auth header.
Click ‘Save’ at the top right corner, then click ‘Test’ to generate a new draft version of the Test App.

For adding a smarthome server on google assistent, a username and password is requested. This can be generated with the /opt/smarthome/WebPassword tool
Any username and password can be chosen. However take care that this password gives access to your system.

Open google assistant on a mobile device.
Go to add device
Search for your action name (probably starting with [test])
Add this device
Log in
Check correct operation with google home app or voice commands

Devices configuration:
------- --------------
(More detailed version to come)
Devices can be configured based on the google smarthome information and the backend that handles the actions.
See https://developers.google.com/assistant/smarthome/guides for more info.
<deviceId> # can be any name
    <type>action.devices.types.SWITCH</type>
    <traits>action.devices.traits.OnOff</traits> # comma separated
    <name>
        <name>Simple switch</name>
        <defaultNames></defaultNames>
        <nickNames></nickNames>
    </name>
    <willReportState>true</willReportState>
    <attributes></attributes>
    <roomHint></roomHint>
    <deviceInfo>
        <manufacturer>smart-home-inc</manufacturer>
        <model>hs1234</model>
        <hwVersion>3.2</hwVersion>
        <swVersion>11.4</swVersion>
    </deviceInfo>
    <backEnd> # Your backend information
        <device>Domotion</device> # Device to control
        <tag>Blinds</tag> # tag as it is called on your device
        <type>SWITCH</type> # type on your device, used as extra check
    </backEnd>
<deviceId>

Backend operators:
------- ----------
To distiguish analog values that may have a digital backend or a different gain or the opposite, special operators may be used.
Analog to digital backend or digital to analog backend (or digital to digital backend):
<trueop>  : can be lt (less than), gt (greater than), le (less or equal than),
            ge (greater or equal than), eq (equal), ne (not equal)
            default: eq
<opval>   : analog value (e.g. 50 if a percentage is given)
            default: 1
<falseval>: analog value for false (e.g. 0)
            default: 0
<trueval> : analog value for true (e.g. 100)
            default: 1

Analog to analog backend:
<a>       : factor a of equation y = a*x + b (where y is the backend value)
            default: 1
<b>       : factor b of equation y = a*x + b (where y is the backend value)
            default: 0

Constant value operator:
<const>   : This value is returned when query. No backend request is done.
            On execute, this command is not executed to backend.

Domotion configuration:
-------- --------------
<smarthomeDomotion>
	<server></server> # can be empty if domotion runs on the same pc
    <port></port> # can be empty if standard port is used
	<username></username> # can be empty if system runs on same pc or local network (equal to Domotion bda username)
	<password></password> # can be empty if system runs on same pc or local network (equal to Domotion bda password)
    <debuglog>false</debuglog> # can be used for extra debug logging of all commands
</smarthomeDomotion>

That's all for now ...

Please send Comments and Bugreports to hellyrulez@home.nl
