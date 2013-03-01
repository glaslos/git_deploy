#!/usr/bin/env python

import json
import urlparse
import sys
import os
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from subprocess import call


class GitDeploy(BaseHTTPRequestHandler):

    CONFIG_FILEPATH = './git_deploy.conf.json'
    config = None
    quiet = False
    daemon = False

    @classmethod
    def get_config(cls):
        if not cls.config:
            try:
                configString = open(cls.CONFIG_FILEPATH).read()
            except:
                sys.exit('Could not load ' + cls.CONFIG_FILEPATH + ' file')
            try:
                cls.config = json.loads(configString)
            except:
                sys.exit(cls.CONFIG_FILEPATH + ' file is not valid json')
            for repository in cls.config['repositories']:
                if not os.path.isdir(repository['path']):
                    sys.exit('Directory ' + repository['path'] + ' not found')
                if not os.path.isdir(repository['path'] + '/.git'):
                    sys.exit('Directory ' + repository['path'] + ' is not a Git repository')
        return cls.config

    def do_POST(self):
        urls = self.parseRequest()
        for url in urls:
            paths = self.getMatchingPaths(url)
            for path in paths:
                self.pull(path)
                self.deploy(path)

    def parseRequest(self):
        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        post = urlparse.parse_qs(body)
        items = []
        for itemString in post['payload']:
            item = json.loads(itemString)
            items.append(item['repository']['url'])
        return items

    def getMatchingPaths(self, repoUrl):
        res = []
        config = self.get_config()
        for repository in config['repositories']:
            if repository['url'] == repoUrl:
                res.append(repository['path'])
        return res

    def respond(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def pull(self, path):
        if not self.quiet:
            print "\nPost push request received"
            print 'Updating ' + path
        call(['cd "' + path + '" && git pull'], shell=True)

    def deploy(self, path):
        config = self.get_config()
        for repository in config['repositories']:
            if repository['path'] == path:
                if 'deploy' in repository:
                    if not self.quiet:
                        print 'Executing deploy command'
                    for cmd in repository['deploy']:
                        call(['cd "' + path + '" && ' + cmd], shell=True)
                break


def main():
    try:
        server = None
        for arg in sys.argv: 
            if arg == '-d' or arg == '--daemon-mode':
                GitDeploy.daemon = True
                GitDeploy.quiet = True
            if arg == '-q' or arg == '--quiet':
                GitDeploy.quiet = True
                
        if GitDeploy.daemon:
            pid = os.fork()
            if pid != 0:
                sys.exit()
            os.setsid()

        if not GitDeploy.quiet:
            print 'Github Autodeploy Service v 0.1 started'
        else:
            print 'Github Autodeploy Service v 0.1 started in daemon mode'
             
        server = HTTPServer(('', GitDeploy.get_config()['port']), GitDeploy)
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        if e:
            print >> sys.stderr, e

        if not server is None:
            server.socket.close()

        if not GitDeploy.quiet:
            print 'Goodbye'

if __name__ == '__main__':
    main()
