import sys
import os.path
from collections import OrderedDict
import json
import awsutils.policies as aws_policies
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

def compareModel2AWS(ctx, policyName, meta):

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
    d = difflib.unified_diff(modelDoc.splitlines(),awsDoc.splitlines(), "AWS","Model", n=0)
    diff = list(d)
    if len(diff) == 0:
        return True, None
    return False, diff

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


def compareAllPolicies(ctx, targetRegion, targetEnv, targetService, targetPolicy, no_diff):
    ctx.vlog('createPolicy(targetRegion: %s targetEnv: %s targetService: %s targetPolicy: %s)' % (targetRegion, targetEnv, targetService, targetPolicy))
    for policyName in ctx.modelPolicies:
        if isValidTarget(ctx,policyName, targetRegion, targetEnv, targetService, targetPolicy) == False:
            continue
        meta = aws_policies.getPolicyMeta(ctx, policyName)
        if meta == None:
                ctx.log('Policy not found at AWS: %s' % policyName)
                continue
        matched, diff = compareModel2AWS(ctx,policyName, meta)
        if matched:
            ctx.log('%s: MATCHED' % policyName)
        else:
            ctx.log('%s: NOT MATCHED' % policyName)
            if not no_diff and diff != None:
                ctx.log("Diff output...")
                for line in diff:
                    click.echo(line)

def updatePolicies(ctx, targetRegion, targetEnv, targetService, targetPolicy, constrainToModel):
    for policyName in ctx.modelPolicies:
        if isValidTarget(ctx,policyName, targetRegion, targetEnv, targetService, targetPolicy) == False:
            continue
        meta = aws_policies.getPolicyMeta(ctx, policyName)
        if meta == None:
            createPolicy(ctx, None, None, None, policyName)
            if ctx.dry_run:
                continue
        meta = aws_policies.getPolicyMeta(ctx, policyName)
        policyArn = meta['Arn']

        matched, diff = compareModel2AWS(ctx,policyName, meta)
        if matched:
            ctx.log('%s: MATCHED' % policyName)
            continue
        if constrainToModel:
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
            policyDocument = json.dumps(modelPolicy)
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
        policyDocument = json.dumps(modelPolicy)
        ctx.log('Creating policy : %s' % policyName)
        aws_policies.createPolicy(ctx, policyName, policyDocument)


def showModel(ctx, targetRegion, targetEnv, targetRole, targetService, targetPolicy):
    print('\nGenerated List of Policies by Role\n')

    for region in ctx.model:
        if targetRegion != None and region != targetRegion:
            continue
        for env in ctx.model[region]:
            if targetEnv != None and env != targetEnv:
                continue
            for role in ctx.model[region][env]:
                if targetRole != None and role != targetRole:
                    continue
                click.echo('Role: %s-%s-%s: ' % (region,env,role))
                for service in ctx.model[region][env][role]:
                    if targetService != None and service != targetService:
                        continue
                    click.echo('%10sService: %s:' % ('',service))
                    for policy in ctx.model[region][env][role][service]:
                        policyName = utils.policyNameFromModel(ctx, region, env, role, service, policy)
                        if targetPolicy != None and policyName != targetPolicy:
                            continue
                        templateName = utils.templateNameFromModel(ctx, service, policy)
                        modelPolicy = json.dumps(ctx.modelPolicies[policyName])
                        width = 120
                        total = len(modelPolicy)
                        lineLen = width - 30
                        begin = 0
                        end = lineLen
                        click.echo('%20sPolicy: %s: ' % ('',policyName))
                        while  begin < total:
                            click.echo('%30s%s'% (' ', modelPolicy[begin:end]))
                            begin += lineLen
                            end += lineLen



def printTemplates(ctx):
    print('\nList of Policy templates\n')
    for name, template in iter(ctx.templates.items()):
        print(name,': ', template)

def showAWSPolicy(ctx, targetRegion, targetEnv, targetService, targetPolicy):

    if targetPolicy != None:
            meta = ctx.awsPolicyMeta[targetPolicy]
            click.echo('%s:  %s' % (targetPolicy, meta) )
            click.echo('')
            policyDocument = aws_policies.getDefaultPolicyVersion(ctx, targetPolicy)
            click.echo(json.dumps(policyDocument))
    else:
        for policyName in ctx.awsPolicyMeta:
            meta = ctx.awsPolicyMeta[policyName]
            click.echo('%s:  %s' % (policyName, meta) )
            click.echo('')
            policyDocument = aws_policies.getDefaultPolicyVersion(ctx, policyName)
            click.echo(json.dumps(policyDocument))
            click.echo('-------------------------------------')
            click.echo('')