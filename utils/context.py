import sys
import os.path
import boto3
import json
import click
from datetime import datetime


class CSMContext(object):
    def __init__(self):
        self.prettyprint = False
        self.verbose = False
        self.orgId=None
        self.dry_run = False
        self.region = None
        self.env = None
        self.iam = boto3.client('iam')
        self.ec2 = boto3.client('ec2')
        self.modelDir = None
        self.modelFile = None
        self.model = None
        self.currentRoles = []
        self.awsPolicyMeta = {}
        self.awsPolicyDocs = {}
        self.modelPolicies=None
        self.templateDir = None
        self.templates = {}
        self.templateExcludes = ['default', 'snippets']

    def arnRoot(self):
        return 'arn:aws:iam::%s' % self.orgId
    def baseName(self):
        return '%s-%s' % (self.region, self.env)
    def basePolicyArn(self):
        return '%s:policy' % self.arnRoot()
    def roleName(self,serviceName):
        return '%s-%s' % (self.baseName(), serviceName)
    def policyArn(self, serviceName):
        return '%s/%s' % (self.basePolicyArn(), self.roleName(serviceName))

    def log(self, msg, *args, color=None):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr,color=color)

    def nlog(self, msg, *args, color=None):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr,color=color, nl=False)

    def audit(self, msg, *args, color=None):
        """Logs a message to stderr."""
        if args:
            msg %= args
        msg2 = '[%s]: %s' % (datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S,%f%z"),msg)
        click.echo(msg2, file=sys.stderr,color=color)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)
    def nvlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.nlog(msg, *args)

    def dumps(self, j):
        if self.prettyprint:
            return json.dumps(j, indent=3)
        else:
            return json.dumps(j)
