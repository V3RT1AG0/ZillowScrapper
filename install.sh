#!/bin/sh
apt-get update  # To get the latest package lists
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install google-chrome-stable -y
apt-get install xvfb -y
apt-get install screen -y
apt-get install python3-pip -y
apt-get install python3-pip -y
virtualenv -p /usr/bin/python3 py3env
source py3env/bin/activate
pip install package-name
pip3 install -U setuptools
pip3 install -r requirements.txt
#etc.