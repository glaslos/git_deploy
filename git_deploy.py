#!/usr/bin/env python

import json
import sys
import os
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from subprocess import call


class GitDeploy(BaseHTTPRequestHandler):

    CONFIG_FILEPATH = './git_deploy.conf.json'
    config = None
    quiet = False
    daemon = False
    branch = None

    @classmethod
    def get_config(cls):
        if not cls.config:
            try:
                config_string = open(cls.CONFIG_FILEPATH).read()
            except IOError:
                sys.exit('Could not load ' + cls.CONFIG_FILEPATH + ' file')
            try:
                cls.config = json.loads(config_string)
            except ValueError:
                sys.exit(cls.CONFIG_FILEPATH + ' file is not valid json')
            for repository in cls.config['repositories']:
                if not os.path.isdir(repository['path']):
                    sys.exit('Directory ' + repository['path'] + ' not found')
                if not os.path.isdir(repository['path'] + '/.git') \
                        and not os.path.isdir(repository['path'] + '/objects'):
                    sys.exit('Directory ' + repository['path'] + ' is not a Git repository')

    def do_POST(self):
        if self.headers.getheader('x-github-event') != 'push':
            if not self.quiet:
                print('We only handle push events')
            self.respond(304)
            return

        self.respond(204)

        urls = self.parse_request()
        for url in urls:
            paths = self.get_matching_paths(url)
            for path in paths:
                self.fetch(path)
                self.deploy(path)

    def parse_request(self):
        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        payload = json.loads(body)
        self.branch = payload['ref']
        return [payload['repository']['url']]

    def get_matching_paths(self, repo_url):
        res = []
        self.get_config()
        for repository in self.config['repositories']:
            if repository['url'] == repo_url:
                res.append(repository['path'])
        return res

    def respond(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def fetch(self, path):
        if not self.quiet:
            print("\nPost push request received")
            print('Updating ' + path)
        call(['cd "' + path + '" && git fetch'], shell=True)

    def deploy(self, path):
        self.get_config()
        for repository in self.config['repositories']:
            if repository['path'] == path:
                if 'deploy' in repository:
                    branch = None
                    if 'branch' in repository:
                        branch = repository['branch']

                    if branch is None or branch == self.branch:
                        if not self.quiet:
                            print('Executing deploy command')
                        call(['cd "' + path + '" && ' + repository['deploy']], shell=True)
                        
                    elif not self.quiet:
                        print('Push to different branch (%s != %s), not deploying' % (branch, self.branch))
                break


def main():
    server = None
    try:
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
            print('Github Autodeploy Service v 0.1 started')
        else:
            print('Github  deploy service v 0.2 started in daemon mode')
             
        server = HTTPServer(('', GitDeploy.get_config()['port']), GitDeploy)
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        if e:
            print(e)

        if server:
            server.socket.close()

        if not GitDeploy.quiet:
            print('Goodbye')

if __name__ == '__main__':
    main()
