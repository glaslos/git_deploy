# Git Auto Deploy

## Introduction

This is a small HTTP server written in python. It allows you to have a version of your project installed,
that will be updated automatically on each Github push.

To set it up, do the following:
* Install python
* Copy the git_deploy.conf.json.dist to git_deploy.conf.json. This file will be gitignored and can be environment specific.
* Enter the matching for your project(s) in the git_deploy.conf.json file
* Start the server by typing "python git_deploy.py" 
* To run it as a daemon add --daemon-mode
* To trigger the pull and deploy via get add --get-to-pull
* On the Github page go to a repository, then "Admin", "Service Hooks", "Post-Receive URLs" and add the url of your machine + port (e.g. http://example.com:8001).

You can even test the whole thing here, by clicking on the "Test Hook" button, whohoo!

## How this works

When someone pushes changes into Github, it sends a json file to the service hook url. 
It contains information about the repository that was updated.

All it really does is match the repository urls to your local repository paths in the config file,move there and run "git pull".


Additionally it runs deploy bash commands that you can add to the config file optionally.
Make sure that you start the server as the user that is allowed to pull from the github repository.
