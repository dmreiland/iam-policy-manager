import sys
import os
import click
import json
import csmutils.model as csm_model
import csmutils.roles as csm_roles
import csmutils.policies as csm_policies
import csmutils.profiles as csm_profiles
import awsutils.roles as aws_roles
import awsutils.policies as aws_policies
import utils.utils as utils
from utils.context import CSMContext

pass_context = click.make_pass_decorator(CSMContext, ensure=True)

@click.group()
@click.version_option()
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode.')
@click.option('--mfa', is_flag=True,
              help='Use MFA for authentication.')
@click.option('--pp', is_flag=True,
              help='Enables pretty print mode.')
@click.option('--model_dir', default='json',
              help='Directory where model file exists')
@click.option('--model_file', default='model-v2.json',
              help='Model file')
@click.option('--templates_folder', default='policy_templates',
              help='Policy templates folder')
@click.option('--org_id', help='Org id for ARNs')
@click.option('--dry_run', is_flag=True, default=False,
              help='Do not make actual changes to AWS')
@pass_context
def cli(ctx, mfa, verbose, pp, model_dir, model_file, templates_folder, org_id, dry_run):
    if 'AWS_REGION' in os.environ:
        ctx.region = os.environ['AWS_REGION']
    elif 'AWS_DEFAULT_REGION' in os.environ:
        ctx.region = os.environ['AWS_DEFAULT_REGION']
    else:
        ctx.log('Error: AWS Region is not defined', color='red')
        sys.exit(1)

    if org_id != None:
        ctx.orgId = org_id
    elif 'AWS_ORG_ID' in os.environ:
        orgid =  os.environ['AWS_ORG_ID']
        if orgid[0] == 'i':
            ctx.orgId = orgid[1:]
        else:
            ctx.orgId = orgid
    else:
        ctx.log('Error: AWS Org ID is not defined', color='red')
        sys.exit(1)

    ctx.verbose = verbose
    ctx.prettyprint = pp
    ctx.dry_run = dry_run
    ctx.modelDir = model_dir
    ctx.modelFile = model_file
    ctx.templateDir = templates_folder

    if mfa:
        ctx.getTempCredentials()
    else:
        ctx.setDefaultClients()

########################################################################
##                       Manage Roles
########################################################################
@cli.group('roles', short_help='manage AWS instance roles')
@pass_context
def roles(ctx):
    ctx.templates = utils.loadPolicyTemplates(ctx)
    ctx.model = utils.loadModel(ctx)
    ctx.modelPolicies = utils.loadModelPolicies(ctx)
    csm_policies.getAWSPolicies(ctx)
    csm_roles.getAWSRoles(ctx)

@roles.command('audit', short_help='Audit AWS roles and policies')
@click.option('-r','--region', help='Audit only this region')
@click.option('-e','--env', help='Audit only this env')
@click.option('--role', help='Audit only for this role in region-env-role format')
@click.option('--no_diff', is_flag=True, help='Do not show diff output', default=False)
@click.option('--diff_type', type=click.Choice(['context','ndiff','unified']), help='Use context style diff output', default='unified')
@click.option('--context_lines', type=click.INT, help='Number of diff context lines to use.', default=0)
@pass_context
def roles_audit(ctx,region, env, role, no_diff, diff_type, context_lines):
    csm_roles.auditRoles(ctx, region, env, role, no_diff, diff_type, context_lines)

@roles.command('compare', short_help='Compare AWS roles to model')
@click.option('-r','--region', help='Compare only for this region')
@click.option('-e','--env', help='Compare only for this env')
@click.option('--role', help='Compare only this role in region-env-role format')
@pass_context
def roles_compare(ctx,region, env, role):
    csm_roles.compareRoles(ctx, region, env, role)

@roles.command('update', short_help='Update AWS roles from model')
@click.option('-r','--region', help='Update only for this region')
@click.option('-e','--env', help='Update only for this env')
@click.option('--role', help='Update only for this role in region-env-role format')
@click.option('--constrain', is_flag=True, default=False,help='Constrain policies to the model')
@pass_context
def roles_update(ctx,region, env, role, constrain):
    csm_roles.updateRoles(ctx, region, env, role, constrain)

@roles.command('show', short_help='Show AWS roles')
@click.option('-r','--region', help='Show only for this region')
@click.option('-e','--env', help='Show only for this env')
@click.option('--role', help='Show only for this role in region-env-role format')
@pass_context
def roles_show_aws(ctx,region, env, role):
    csm_roles.showRoles(ctx, region, env, role)

@roles.command('delete', short_help='Deleta an AWS role')
@click.option('--role', help='Role in region-env-role format')
@pass_context
def roles_delete_aws(ctx, role):
    csm_roles.deleteRole(ctx, role)

########################################################################
##                       Manage Instance Profiles
########################################################################
@cli.group('profiles', short_help='manage AWS  instance profiles')
@pass_context
def profiles(ctx):
    ctx.templates = utils.loadPolicyTemplates(ctx)
    ctx.model = utils.loadModel(ctx)
    ctx.modelPolicies = utils.loadModelPolicies(ctx)
    csm_policies.getAWSPolicies(ctx)
    csm_roles.getAWSRoles(ctx)


@profiles.command('show', short_help='Show AWS Instance Profiles')
@click.option('-r','--region', help='Show only for this region')
@click.option('-e','--env', help='Show only for this env')
@click.option('--profilename', help='Show only for this profile name')
@click.option('--id', help='Show only for this profile id')
@click.option('--instances', is_flag=True, help='Show associated instances', default=False)
@pass_context
def profiles_show(ctx, region, env, profilename, id, instances):
    csm_profiles.showInstanceProfiles(ctx, region, env, profilename, id, instances)


########################################################################
##                       Manage Policies
########################################################################
@cli.group('policies', short_help='manage AWS  policies')
@pass_context
def policies(ctx):
    ctx.templates = utils.loadPolicyTemplates(ctx)
    ctx.model = utils.loadModel(ctx)
    ctx.modelPolicies = utils.loadModelPolicies(ctx)
    csm_policies.getAWSPolicies(ctx)
    csm_roles.getAWSRoles(ctx)


@policies.command('delete', short_help='Compare model and AWS')
@click.option('-p','--policy', help='Create only this Policy')
@pass_context
def policies_delete(ctx, policy):
    aws_policies.deletePolicy(ctx, policy)


@policies.command('create', short_help='Compare model and AWS')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Create only this Policy')
@pass_context
def policies_create(ctx, region, env, service, policy):
    csm_policies.createPolicy(ctx,region,env,service,policy)

@policies.command('compare', short_help='Compare model and AWS')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Show only for this policy')
@click.option('--no_diff', is_flag=True, help='Do not show diff output', default=False)
@click.option('--diff_type', type=click.Choice(['context','ndiff','unified']), help='Use context style diff output', default='unified')
@click.option('--context_lines', type=click.INT, help='Number of diff context lines to use.', default=0)
@pass_context
def policies_compare(ctx, region, env, service, policy, no_diff, diff_type, context_lines):
    csm_policies.compareAllPolicies(ctx, region, env, service, policy, no_diff, diff_type, context_lines)

@policies.command('update', short_help='Compare model and AWS')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Show only for this policy')
@click.option('--constrain', is_flag=True, default=False,help='Constrain policies to the model')
@click.option('--force', is_flag=True, default=False,help='Force a document upgrade, even if it matches')
@pass_context
def policies_update(ctx, region, env, service, policy, constrain, force):
    csm_policies.updatePolicies(ctx, region, env, service, policy, constrain, force)

@policies.command('show', short_help='Show the current AWS policy(s)')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Show only for this policy')
@pass_context
def policies_show_aws_policy(ctx, region, env, service, policy):
    csm_policies.showAWSPolicy(ctx, region, env, service, policy)

@policies.command('show_unattached', short_help='Show all unattached policies not in the model')
@pass_context
def policies_show_model_policy(ctx):
    notInModel = True
    unattached = True
    csm_policies.showAWS(ctx, notInModel, unattached)


########################################################################
##                       Model Commands
########################################################################
@cli.group('model', short_help='manage the model')
@pass_context
def model(ctx):
    ctx.templates = utils.loadPolicyTemplates(ctx)
    ctx.model = utils.loadModel(ctx)
    ctx.modelPolicies = utils.loadModelPolicies(ctx)
    #csm_policies.getAWSPolicies(ctx)
    #csm_roles.getAWSRoles(ctx)

@model.command('show', short_help='Show the model')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('--role', help='Create only for this role')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Show only for this policy')
@pass_context
def model_show(ctx, region, env, role, service, policy):
    csm_model.showModel(ctx, region, env, role, service, policy)

@model.command('json', short_help='Show the instantiated model object')
@pass_context
def model_json(ctx):
    csm_model.showModeJson(ctx)
