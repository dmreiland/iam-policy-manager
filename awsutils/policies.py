import sys
import os.path
import boto3
from botocore.exceptions import ClientError
import json
import click
from jinja2 import Template
import utils.utils as utils
from awsutils import roles as aws_roles

def guessIamArn(ctx, policyName):
    return 'arn:aws:iam::%s:policy/%s' % (ctx.orgId, policyName)

def storePolicyMeta(ctx, meta):
    ctx.awsPolicyMeta[meta['PolicyName']]=meta

def storePolicyMetas(ctx, metas):
    for meta in metas:
        storePolicyMeta(ctx, meta)

def fetchPolicy(ctx, policyName):
    iam = ctx.iam
    policyArn = guessIamArn(ctx,policyName)
    try:
        mps = iam.get_policy(PolicyArn=policyArn)
        if mps == None:
            ctx.vlog('fetchPolicy: policy not found for %s (%s)' % policyName, policyArn)
        ctx.vlog('fetchPolicy: fetched meta for %s\n%s' % (policyName, mps))
        ctx.awsPolicyMeta[policyName] = mps['Policy']
    except ClientError as err:
        ctx.vlog('fetchPolicy: policy not found for %s (%s)' % (policyName, policyArn))


def getPolicyMeta(ctx, policyName):
    if policyName not in ctx.awsPolicyMeta:
        ctx.vlog('getPolicyMeta: %s is not in cache.  Attempting to fetch' % policyName)
        fetchPolicy(ctx, policyName)
    if policyName not in ctx.awsPolicyMeta:
        ctx.log('getPolicyMeta: %s was not found in AWS' % policyName)
        return None
    return ctx.awsPolicyMeta[policyName]

def getAllPolicies(ctx, env=None):
    iam = ctx.iam
    mps = iam.list_policies(Scope='Local')
    storePolicyMetas(ctx,mps['Policies'])
    while mps['IsTruncated']:
        mps = iam.list_policies(Scope='Local', Marker=mps['Marker'])
        storePolicyMetas(ctx,mps['Policies'])

def getPolicyVersions(ctx, policyArn):
    iam = ctx.iam
    versions = []
    mps = iam.list_policy_versions(PolicyArn = policyArn)
    ctx.vlog('getPolicyVersions: received \n%s' % mps)
    for version in mps['Versions']:
        versions.append(version['VersionId'])
    while mps['IsTruncated']:
        mps = iam.list_policy_versions(PolicyArn = policyArn, Marker=mps['Marker'])
        for version in mps['Versions']:
            versions.append(version['VersionId'])
    return versions

def createPolicyVersion(ctx, policyArn, policyDocument):
    iam = ctx.iam
    if ctx.dry_run:
        ctx.log('create_policy_version(PolicyArn=%s, PolicyDocument=%s,SetAsDefault=True)' % (policyArn,policyDocument))
        return
    mps = iam.create_policy_version(PolicyArn=policyArn, PolicyDocument=policyDocument,SetAsDefault=True)
    ctx.audit('Created new default policy version for policy %s: %s' % (policyArn, policyDocument))
    policyName = utils.policyNameFromArn(ctx, policyArn)
    getDefaultPolicyVersion(ctx, policyName)

def deletePolicyVersion(ctx, policyArn, versionId):
    iam = ctx.iam
    if ctx.dry_run:
        ctx.log('delete_policy_version(PolicyArn=%s,VersionId=%s)' % (policyArn, versionId))
        return
    iam.delete_policy_version(PolicyArn=policyArn,VersionId=versionId)
    ctx.audit('Deleted policy version %s from %s' % (versionId, policyArn))


def getDefaultPolicyVersion(ctx, policyName):
    iam = ctx.iam
    meta = getPolicyMeta(ctx,policyName)
    if meta == None:
        ctx.log('getDefaultPolicyVersion: Error - getPolicyMeta returned None for %s'%policyName)
        sys.exit(1)
    if policyName in ctx.awsPolicyDocs:
        ctx.vlog('getDefaultPolicyVersion: Returning cached policy document')
        return ctx.awsPolicyDocs[policyName]

    ctx.vlog('getDefaultPolicyVersion: Getting policy document from AWS')
    policyArn = meta['Arn']
    versionId = meta['DefaultVersionId']
    mps = iam.get_policy_version(PolicyArn=policyArn, VersionId=versionId)
    policyDoc = mps['PolicyVersion']['Document']
    ctx.awsPolicyDocs[policyName] = policyDoc
    return policyDoc


def deletePolicy(ctx, policyName):
    iam = ctx.iam
    meta = getPolicyMeta(ctx, policyName)
    if meta == None:
        # Nothing to do
        ctx.vlog('deletePolicy: policy %s does not exist' % policyName)
        return
    policyArn = meta['Arn']
    defaultVersionId = meta['DefaultVersionId']

    #detach from Roles
    #try:
    mps = iam.list_entities_for_policy(PolicyArn=policyArn, EntityFilter='Role')
    # {'PolicyUsers': [], 'ResponseMetadata': {'HTTPStatusCode': 200, 'RequestId': '15a1da6e-83eb-11e5-95da-2d6fbedc8b89'}, 'PolicyGroups': [], 'IsTruncated': False, 'PolicyRoles': [{'RoleName': 'us-west-2-dev-mongo'}]}

    for policyRole in mps['PolicyRoles']:
        roleName = policyRole['RoleName']
        aws_roles.detachPolicy(ctx, roleName, policyName)

    while mps['IsTruncated']:
        mps = iam.list_entities_for_policy(PolicyArn=policyArn, EntityFilter='Role', Marker=mps['Marker'])
        for policyRole in mps['PolicyRoles']:
            aws_roles.detachPolicy(ctx, policyRole['RoleName'], policyName)
    #except:
    #    pass

    # delete all Versions except Default
    versions = getPolicyVersions(ctx, policyArn)
    for versionId in versions:
        if versionId != defaultVersionId:
            deletePolicyVersion(ctx, policyArn, versionId)

    # delete the policy
    iam.delete_policy(PolicyArn=policyArn)
    ctx.audit('Deleted policy %s' % (policyName))

def createPolicy(ctx, policyName, policyDocument):
    ctx.vlog('iam.create_policy(PolicyName=%s, PolicyDocument=%s)'%(policyName, policyDocument))
    iam = ctx.iam
    if ctx.dry_run:
        ctx.log('create_policy(PolicyName=%s, PolicyDocument=%s)' % (policyName, policyDocument))
        return
    mps = iam.create_policy(PolicyName=policyName, PolicyDocument=policyDocument)
    ctx.audit('Created policy %s with %s' % (policyName, policyDocument))
    if mps['ResponseMetadata']['HTTPStatusCode'] == 200:
        ctx.log('Policy created: %s' % mps['Policy']['Arn'])
        storePolicyMeta(ctx, mps['Policy'])
        getDefaultPolicyVersion(ctx, mps['Policy']['PolicyName'])
    ctx.vlog(mps)
