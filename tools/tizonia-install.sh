#!/bin/bash
#
# Copyright (C) 2011-2015 Aratelia Limited - Juan A. Rubio
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Script that installs Tizonia's debian packages and its dependencies.
#

if cat /etc/*-release | grep raspbian; then
  DISTRO="raspbian" ; RELEASE=jessie
elif cat /etc/*-release | grep jessie; then
  DISTRO="jessie" ; RELEASE=jessie
elif cat /etc/*-release | grep trusty; then
  DISTRO="ubuntu" ; RELEASE=trusty
else
  echo "Can't find a supported debian-based distribution."
  exit 1
fi

# Make sure curl is already installed
sudo apt-get -y install curl

# Add Mopidy's archive to APT's sources.list
grep -q "apt.mopidy.com" /etc/apt/sources.list
if [ $? -eq 1 ]; then
    curl 'http://apt.mopidy.com/mopidy.gpg' | sudo apt-key add -
    echo "deb http://apt.mopidy.com/ stable main contrib non-free" | sudo tee -a /etc/apt/sources.list
fi

# Add Tizonia's archive to APT's sources.list
grep -q "dl.bintray.com/tizonia" /etc/apt/sources.list
if [ $? -eq 1 ]; then
    curl 'https://bintray.com/user/downloadSubjectPublicKey?username=tizonia' | sudo apt-key add -
    echo "deb https://dl.bintray.com/tizonia/$DISTRO $RELEASE main" | sudo tee -a /etc/apt/sources.list
fi

# Resynchronize APT's package index files
sudo apt-get update

# Install Simon Weber's gmusicapi
sudo apt-get -y install python-pip \
    && ( sudo pip install gmusicapi || sudo pip install gmusicapi )

# Install libspotify
sudo apt-get -y install libspotify12

# Install Tizonia
sudo apt-get -y install tizonia-all

# Copy Tizonia's config file
if [ ! -e "$HOME"/.config/tizonia/tizonia.conf ]; then
    cp /etc/tizonia/tizonia.conf/tizonia.conf "$HOME"/.config/tizonia/tizonia.conf
fi
