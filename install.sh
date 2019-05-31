#!/bin/sh
apt-get update  # To get the latest package lists
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install google-chrome-stable -y
apt-get install xvfb -y
apt-get install screen -y
pip install -r requirements.txt
#etc.