import sys
import os.path
from collections import OrderedDict
import json
import awsutils.policies as aws_policies
import awsutils.instances as aws_instances
import utils.utils as utils
import click
import difflib
from utils.utils import Reorder

policyTemplates={}

###############################################################################
#     Policy Management Routines
###############################################################################


def getAWSPolicies(ctx):
    ctx.vlog('getAWSPolicies: Getting all policy metadata from AWS')
    aws_policies.getAllPolicies(ctx)

def getAWSPolicyDocument(ctx, policyName):
    meta = aws_policies.getPolicyMeta(ctx, policyName)
    if meta == None:
        ctx.log('AWS policy %s was not found' % policyName)
    else:
        policyDoc = aws_policies.getDefaultPolicyVersion(ctx, policyName)
        return policyDoc

def getModelPolicyDocument(ctx, policyName):
    if policyName not in ctx.modelPolicies:
        ctx.log("Model policy %s was not found" % policyName)
    else:
        policyDoc = ctx.modelPolicies[policyName]
        return policyDoc

def compareModel2AWS(ctx, policyName, meta, diff_type, context_lines):

    docModel = ['Version','Statement']
    stmtModel = ['Effect','Action','Resource']
    statement = Reorder()
    statement.model = stmtModel
    document = Reorder()
    document.model = docModel

    ctx.vlog('Fetching AWS policy: %s' % policyName)
    awsPolicy = aws_policies.getDefaultPolicyVersion(ctx, policyName)
    if awsPolicy == None:
        return False, None
    awsPolicy = document.do(awsPolicy)
    awsPolicy['Statement'] = statement.dolist(awsPolicy['Statement'])
    awsDoc = json.dumps(awsPolicy, indent=4)

    ctx.vlog('Fetching Model policy')
    modelPolicy = getModelPolicyDocument(ctx, policyName)
    modelDoc = json.dumps(modelPolicy, indent=4)
    matched = True
    diff = None
    if diff_type == 'context':
        d = difflib.context_diff(modelDoc.splitlines(),awsDoc.splitlines(), "AWS","Model", n=context_lines)
        dd = list(d)
        if len(dd) > 0:
            matched = False
            diff = dd
    elif diff_type == 'ndiff':
        d = difflib.ndiff(modelDoc.splitlines(),awsDoc.splitlines())
        dd = list(d)
        for line in dd:
            if line[0] == '-' or line[0] == '+'  or line[0] == '?':
                matched = False
                diff = dd

    else:
        d = difflib.unified_diff(modelDoc.splitlines(),awsDoc.splitlines(), "AWS","Model", n=context_lines)
        dd = list(d)
        if len(dd) > 0:
            matched = False
            diff = dd

    return matched, diff

def isValidTarget(ctx,policyName, targetRegion, targetEnv, targetService, targetPolicy):
    if targetPolicy != None and policyName != targetPolicy:
        return False
    region, env, service = utils.regionEnvAndRole(policyName)
    if targetRegion != None and region != targetRegion:
        return False
    if targetEnv != None and env != targetEnv:
        return False
    if targetService != None and service != targetService:
        return False
    return True


def compareAllPolicies(ctx, targetRegion, targetEnv, targetService, targetPolicy, no_diff, diff_type, context_lines):

    for policyName in ctx.modelPolicies:
        if isValidTarget(ctx,policyName, targetRegion, targetEnv, targetService, targetPolicy) == False:
            continue
        meta = aws_policies.getPolicyMeta(ctx, policyName)
        if meta == None:
                ctx.log(click.style('Policy not found at AWS: %s' % policyName, fg='cyan'))
                continue
        matched, diff = compareModel2AWS(ctx,policyName, meta, diff_type, context_lines)
        if matched:
            ctx.log('%s: MATCHED' % policyName)
        else:
            ctx.log(click.style('%s: NOT MATCHED' % policyName, fg='cyan'))
            if not no_diff and diff != None:
                ctx.log("Diff output...")
                for line in diff:
                    click.echo(line)

def updatePolicies(ctx, targetRegion, targetEnv, targetService, targetPolicy, constrainToModel, force):
    for policyName in ctx.modelPolicies:
        if isValidTarget(ctx,policyName, targetRegion, targetEnv, targetService, targetPolicy) == False:
            continue
        meta = aws_policies.getPolicyMeta(ctx, policyName)
        if meta == None:
            ctx.log('Adding model policy not found in AWS: %s' % policyName)
            createPolicy(ctx, None, None, None, policyName)
            continue

        ctx.log('Model policy found in AWS: %s.  Comparing policy document' % policyName)
        policyArn = meta['Arn']

        if force:
            ctx.log('Forcing an update.  No compare necessary.')
        else:
            matched, diff = compareModel2AWS(ctx,policyName, meta,'unified',0)
            if matched:
                ctx.log('%s: MATCHED.  Noting to update.' % policyName)
                continue

        ctx.log('%s: DID NOT MATCH' % policyName)
        if force or constrainToModel:
            # Need to update the policy.  Get the number of
            versions = aws_policies.getPolicyVersions(ctx,meta['Arn'])
            if len(versions) >= 5:
                # Too many versions, gotta delete 1
                versions.sort()
                defaultVersionId = meta['DefaultVersionId']
                for version in versions:
                    if version != defaultVersionId:
                        aws_policies.deletePolicyVersion(ctx,policyArn, version)
                        break
            modelPolicy = getModelPolicyDocument(ctx, policyName)
            policyDocument = json.dumps(modelPolicy,indent=4)
            aws_policies.createPolicyVersion(ctx, policyArn, policyDocument)



def createPolicy(ctx, targetRegion, targetEnv, targetService, targetPolicy):
    policies = ctx.modelPolicies
    ctx.vlog('createPolicy(targetRegion: %s targetEnv: %s targetService: %s targetPolicy: %s)' % (targetRegion, targetEnv, targetService, targetPolicy))
    for policyName in ctx.modelPolicies:
        if isValidTarget(ctx,policyName, targetRegion, targetEnv, targetService, targetPolicy) == False:
            continue
        # See if this policy is already in aws
        if aws_policies.getPolicyMeta(ctx,policyName) != None:
            ctx.log('%s already exists' % policyName)
            continue
        modelPolicy = getModelPolicyDocument(ctx, policyName)
        if modelPolicy == None:
            ctx.log('Error: %s does not exist in the model' % policyName)
            continue
        policyDocument = json.dumps(modelPolicy, indent=4)
        ctx.log('Creating policy : %s' % policyName)
        aws_policies.createPolicy(ctx, policyName, policyDocument)


def showAWSPolicy(ctx, targetRegion, targetEnv, targetService, targetPolicy):

    if targetPolicy != None:
            meta = ctx.awsPolicyMeta[targetPolicy]
            click.echo('%s:  %s' % (targetPolicy, meta) )
            click.echo('')
            policyDocument = aws_policies.getDefaultPolicyVersion(ctx, targetPolicy)
            click.echo(ctx.dumps(policyDocument))
    else:
        for policyName in ctx.awsPolicyMeta:
            meta = ctx.awsPolicyMeta[policyName]
            click.echo('%s:  %s' % (policyName, meta) )
            click.echo('')
            policyDocument = aws_policies.getDefaultPolicyVersion(ctx, policyName)
            click.echo(ctx.dumps(policyDocument))
            click.echo('-------------------------------------')
            click.echo('')

def showAWS(ctx, notInModel, unattached):
    for policyName in ctx.awsPolicyMeta:
        meta = ctx.awsPolicyMeta[policyName]
        attachments = meta['AttachmentCount']
        if unattached and attachments > 0:
            continue
        if notInModel and policyName in ctx.modelPolicies:
            continue
        ctx.log(click.style('%s is not in the model, and has %d attached entities' % (policyName, attachments),fg='cyan'))
