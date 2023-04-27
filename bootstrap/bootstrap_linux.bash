#!/bin/bash

# This script is used to setup a linux box for use with PyExpLabSys

##############################################################
# EDIT POINT START: Edit here to change what the script does #
##############################################################

# Usage string, edit if adding another section to the script
usage="This is the SurfCat Linux bootstrap script

    USAGE: bootstrap_linux.bash SECTION

Where SECTION is the part of the bootstrap script that you want to run, listed below. If the value of \"all\" is given all section will be run. NOTE you can only supply one argument:

Sections:
git         Add common git aliases
autostart   Setup autostart cronjob
settings    Link in the PyExpLabSys settings file

all         All of the above
"
##################
# EDIT POINT END #
##################

# Functions
echobad(){
    echo -e "\033[1m\E[31m$@\033[0m"
}

echobold(){
    echo -e "\033[1m$@\033[0m"
}

echogood(){
    echo -e "\033[1m\E[32m$@\033[0m"
}

echoblue(){
    echo -e "\033[1m\E[34m$@\033[0m"
}

echoyellow(){
    echo -e "\033[1m\E[33m$@\033[0m"
}

# Checks argument number and if needed print usage
if [ $# -eq 0 ] || [ $# -gt 1 ];then
    echo "$usage"
    exit
fi

# Git section
if [ $1 == "git" ] || [ $1 == "all" ];then
    echo
    echobold "===> SETTING UP GIT"
    echoblue "---> Setting up git aliases"
    echoblue "----> ci='commit -v'"
    git config --global alias.ci 'commit -v'
    echoblue "----> pr='pull --rebase'"
    git config --global alias.pr 'pull --rebase'
    echoblue "----> lol='log --graph --decorate --pretty=oneline --abbrev-commit'"
    git config --global alias.lol 'log --graph --decorate --pretty=oneline --abbrev-commit'
    echoblue "----> ba='branch -a'"
    git config --global alias.ba 'branch -a'
    echoblue "----> st='status'"
    git config --global alias.st 'status'
    echoblue "----> cm='commit -m'"
    git config --global alias.cm 'commit -m'
    echoblue "---> Make git use colors"
    git config --global color.ui true
    echoblue "---> Set default push setting"
    git config --global push.default matching
    echogood "+++++> DONE"
fi

# Setup autostart cronjob
if [ $1 == "autostart" ] || [ $1 == "all" ];then
    echo
    echobold "===> SETTINGS UP AUTOSTART CRONJOB"

    # Form path of autostart script
    autostartpath="/home/$USER/PyExpLabSys/bin/autostart.py" # not friendly to Windows
    cronline="@reboot SHELL=/bin/bash BASH_ENV=$HOME/.bashrc \
/usr/bin/env python $autostartpath 2>&1 | \
/usr/bin/logger -t cinfautostart"

    echoblue "Using autostart path: $autostartpath"

    # Check if there has been installed cronjobs before
    crontab -l > /dev/null
    if [ $? -eq 0 ];then
        crontab -l | grep $autostartpath > /dev/null
        if [ $? -eq 0 ];then
            echoblue "Autostart cronjob already installed"
        else
            crontab -l | { cat; echo $cronline; } | crontab -
            echoblue "Installed autostart cronjob"
        fi
    else
        cronlines="# Output of the crontab jobs (including errors) is sent through\n\
# email to the user the crontab file belongs to (unless redirected).\n\
#\n\
# For example, you can run a backup of all your user accounts\n\
# at 5 a.m every week with: # 0 5 1 tar -zcf /var/backups/home.tgz /home/\n\
#\n\
# For more information see the manual pages of crontab(5) and cron(8)\n\
#\n\
# m h dom mon dow command\n\
$cronline"
        crontab -l | { cat; echo -e $cronlines; } | crontab -
        echoblue "Had no cronjobs. Installed with standard header."
    fi
    echogood "+++++> DONE"
fi

# Setup settings file for PyExpLabSys
if [ $1 == "settings" ] || [ $1 == "all" ];then
    echobold "===> SETTING UP A PYEXPLABSYS SETTINGS FILE"
    if [ -f ~/.config/PyExpLabSys/user_settings.yaml ];then
        echogood "Settings file already exists - remove if you want to overwrite it"
    else
        echoblue "---> Make ~/.config/PyExpLabSys dir"
        mkdir -p ~/.config/PyExpLabSys
        echoblue "---> Link settings into dir:"
        echoblue "---> ~/machines/bootstrap/user_settings.yaml into ~/.config/PyExpLabSys/"
        cp ~/machines/bootstrap/user_settings.yaml ~/.config/PyExpLabSys/user_settings.yaml
    fi
    echogood "+++++> DONE"
fi
