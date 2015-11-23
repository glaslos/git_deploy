#!/usr/bin/env python

import json
import sys
import os
import hmac
import hashlib
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from subprocess import call


class GitDeploy(BaseHTTPRequestHandler):

    CONFIG_FILEPATH = './git_deploy.conf.json'
    config = None
    quiet = False
    daemon = False
    branch = None
    is_get_available = False

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
        return cls.config

    def do_GET(self):
        if GitDeploy.is_get_available:
            paths = [repository['path'] for repository in self.get_config()['repositories']]
            for path in paths:
                self.pull(path)
                self.deploy(path)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html>")
            self.wfile.write("<head><title>Github Autodeploy</title></head>")
            self.wfile.write("<body><p>Ok, updated.</p></body>")
            self.wfile.write("</html>")
        else:
            self.send_response(500)

    def get_payload(self):
        length = int(self.headers.getheader('content-length'))
        body = self.rfile.read(length)
        payload = json.loads(body)
        return body, payload

    def _validate_signature(self, secret, data):
        sha_name, signature = self.headers.getheader('X-Hub-Signature').split('=')
        if sha_name != 'sha1':
            return False

        # HMAC requires its key to be bytes, but data is strings.
        mac = hmac.new(bytes(secret), msg=data, digestmod=hashlib.sha1)
        return mac.hexdigest() == signature

    def check_hmac_signature(self, body, urls):
        signature = self.headers.getheader('X-Hub-Signature')
        if not signature:
            return True

        config = self.get_config()
        secret = None
        for url in urls:
            for repository in config['repositories']:
                if repository['url'] == url:
                    if 'secret' in repository:
                        secret = repository['secret']
        if not secret:
            if not self.quiet:
                print('No secret configured')
            self.respond(304)
            return False

        if not self._validate_signature(secret, body):
            if not self.quiet:
                print('Bad request signature')
            self.respond(304)
            return False

        return True

    def do_POST(self):
        event = self.headers.getheader('X-Github-Event')
        body, payload = self.get_payload()
        try:
            urls = self.parse_rq(payload)
        except Exception as e:
            if not self.quiet:
                print('Cannot parse url. Invalid payload: {}'.format(e))
            self.respond(304)
            return
        if not self.check_hmac_signature(body, urls):
            return
        if event == 'ping':
            if not self.quiet:
                print('Ping event received')
            self.respond(204)
            return
        if event != 'push':
            if not self.quiet:
                print('We only handle ping and push events')
            self.respond(304)
            return

        self.respond(204)

        self.respond(200)
        for url in urls:
            paths = self.get_matching_paths(url)
            for path in paths:
                self.fetch(path)
                self.deploy(path)

    def parse_rq(self, payload=None):
        if payload:
            if 'ref' in payload:
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
        gitcmd = 'git fetch'
        config = self.get_config()
        for repository in config['repositories']:
            if repository['path'] == path:
                if 'gitcmd' in repository:
                    gitcmd = repository['gitcmd']
                break
        if not self.quiet:
            print("\nPost push request received")
            print('Updating ' + path)
        call(['cd "' + path + '" && ' + gitcmd], shell=True)

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
            if arg == '-g' or arg == '--get-to-pull':
                GitDeploy.is_get_available = True

        if GitDeploy.daemon:
            pid = os.fork()
            if pid != 0:
                sys.exit()
            os.setsid()

        print('Github deploy service v 0.3 started in daemon mode')

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
