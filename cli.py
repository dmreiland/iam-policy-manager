import sys
import os
import click
import json
from utils.context import CSMContext
import csmutils.roles as csm_roles
import awsutils.roles as aws_roles
import csmutils.policies as csm_policies
import awsutils.policies as aws_policies
import utils.utils as utils

pass_context = click.make_pass_decorator(CSMContext, ensure=True)

@click.group()
@click.version_option()
@click.option('-v', '--verbose', is_flag=True,
              help='Enables verbose mode.')
@click.option('--default_roles_file', default='default_roles.json',
              help='Default roles model file')
@click.option('--model_file', default='model.json',
              help='Model file')
@click.option('--templates_folder', default='policy_templates',
              help='Policy templates folder')
@click.option('--org_id', default='716927822216',
              help='Org id for ARNs')
@click.option('--dry_run', is_flag=True, default=False,
              help='Do not make actual changes to AWS')
@pass_context
def cli(ctx, verbose, default_roles_file, model_file, templates_folder, org_id, dry_run):
    if 'AWS_REGION' in os.environ:
        ctx.region = os.environ['AWS_REGION']
    elif 'AWS_DEFAULT_REGION' in os.environ:
        ctx.region = os.environ['AWS_DEFAULT_REGION']
    else:
        ctx.log('Error: AWS Region is not defined', color='red')
        sys.exit(1)

    ctx.verbose = verbose
    ctx.dry_run = dry_run
    ctx.modelFile = model_file
    ctx.defaultRolesFile = default_roles_file
    ctx.templateDir = templates_folder
    ctx.orgId = org_id

    ctx.templates = utils.loadPolicyTemplates(ctx)
    ctx.model = utils.loadModel(ctx)
    ctx.modelPolicies = utils.loadModelPolicies(ctx)
    csm_policies.getAWSPolicies(ctx)
    csm_roles.getAWSRoles(ctx)

########################################################################
##                       Manage Roles
########################################################################
@cli.group('roles', short_help='manage AWS instance roles')
@pass_context
def roles(ctx):
    pass
@roles.command('compare', short_help='Compare AWS roles to model')
@click.option('-r','--region', help='Compare only for this region')
@click.option('-e','--env', help='Compare only for this env')
@click.option('-i','--role', help='Compare only for this role')
@click.option('--rolename', help='Update only for this role in region-env-role format')
@pass_context
def roles_compare(ctx,region, env, role, rolename):
    compareOnly = True
    constrain = False
    csm_roles.compareRoles(ctx, region, env, role, rolename, compareOnly, constrain)

@roles.command('update', short_help='Update AWS roles from model')
@click.option('-r','--region', help='Update only for this region')
@click.option('-e','--env', help='Update only for this env')
@click.option('-i','--role', help='Update only for this role in region, env, role format')
@click.option('--rolename', help='Update only for this role in region-env-role format')
@click.option('--constrain', is_flag=True, default=False,help='Constrain policies to the model')
@pass_context
def roles_update(ctx,region, env, role, rolename, constrain):
    compareOnly = False
    csm_roles.compareRoles(ctx, region, env, role, rolename, compareOnly, constrain)

@roles.command('show_aws', short_help='Show AWS roles')
@click.option('-r','--region', help='Show only for this region')
@click.option('-e','--env', help='Show only for this env')
@click.option('-i','--role', help='Show only for this role in region, env, role format')
@click.option('--rolename', help='Show only for this role in region-env-role format')
@pass_context
def roles_show_aws(ctx,region, env, role, rolename):
    csm_roles.showAwsRoles(ctx, region, env, role, rolename)

@roles.command('delete', short_help='Deleta an AWS role')
@click.option('--rolename', help='Role in region-env-role format')
@pass_context
def roles_delete_aws(ctx, rolename):
    aws_roles.deleteRole(ctx, rolename)


########################################################################
##                       Manage Policies
########################################################################
@cli.group('policies', short_help='manage AWS  policies')
@pass_context
def policies(ctx):
    pass


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
@pass_context
def policies_compare(ctx, region, env, service, policy, no_diff):
    csm_policies.compareAllPolicies(ctx, region, env, service, policy, no_diff)

@policies.command('update', short_help='Compare model and AWS')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Show only for this policy')
@click.option('--constrain', is_flag=True, default=False,help='Constrain policies to the model')
@pass_context
def policies_compare(ctx, region, env, service, policy, constrain):
    csm_policies.updatePolicies(ctx, region, env, service, policy, constrain)

@policies.command('show_model', short_help='Show the model')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('-i','--role', help='Create only for this role')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Show only for this policy')
@pass_context
def policies_show_model(ctx, region, env, role, service, policy):
    csm_policies.showModel(ctx, region, env, role, service, policy)

@policies.command('show_aws_policy', short_help='Show an AWs policy')
@click.option('-r','--region', help='Create only for this region')
@click.option('-e','--env', help='Create only for this env')
@click.option('-s','--service', help='Create only for this service')
@click.option('-p','--policy', help='Show only for this policy')
@pass_context
def policies_show_aws_policy(ctx, region, env, service, policy):
    csm_policies.showAWSPolicy(ctx,region, env, service, policy)

@policies.command('show_model_policy', short_help='Show an AWs policy')
@click.option('-p','--policy', help='Policy name')
@pass_context
def policies_show_model_policy(ctx, policy):
    policyDoc = csm_policies.getModelPolicyDocument(ctx,policy)
    click.echo(json.dumps(policyDoc,indent=4))
