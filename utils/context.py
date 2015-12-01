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
        self.iam = None
        self.ec2 = None
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

    def log(self, text, nl=True, err=False, color=None, **styles):
        """Logs a message to stderr."""
        click.secho(text, file=sys.stderr, nl=nl, err=err, color=color, **styles)

    def audit(self, text, nl=True, err=False, color=None, **styles):
        """Logs a message to stderr with timestamp."""
        text2 = '[%s]: %s' % (datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S,%f%z"),text)
        self.log(text2, nl=nl, err=err, color=color, **styles)

    def vlog(self, text, nl=True, err=False, color=None, **styles):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(text, nl=nl, err=err, color=color, **styles)

    def dumps(self, j):
        if self.prettyprint:
            return json.dumps(j, indent=3)
        else:
            return json.dumps(j)

    def setDefaultClients(self):
        self.iam = boto3.client('iam')
        self.ec2 = boto3.client('ec2')

    def getTempCredentials(self):
        mfa_deviceId = click.prompt("Enter Your AWS user name: ")
        mfa_TOTP = click.prompt("Enter the MFA code: ")
        sts_connection = boto3.client('sts')
        tempCredentials = sts_connection.get_session_token(
            DurationSeconds=3600,
            SerialNumber='arn:aws:iam::%s:mfa/%s' % (self.orgId, mfa_deviceId),
            TokenCode=mfa_TOTP)
        self.iam = boto3.client(
            'iam',
            aws_access_key_id=tempCredentials['Credentials']['AccessKeyId'],
            aws_secret_access_key=tempCredentials['Credentials']['SecretAccessKey'],
            aws_session_token=tempCredentials['Credentials']['SessionToken'])
        self.ec2 = boto3.client(
            'ec2',
            aws_access_key_id=tempCredentials['Credentials']['AccessKeyId'],
            aws_secret_access_key=tempCredentials['Credentials']['SecretAccessKey'],
            aws_session_token=tempCredentials['Credentials']['SessionToken'])
