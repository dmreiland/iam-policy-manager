<h1> AWS Role/Policy Utility</h1>

This utility helps manage AWS IAM Roles, and their associated Policies
via a simple model.

<h2>Installation</h2>
This utility is distributed as a python module, ready to be installed with pip.

This app requires python 3

To install into a virtual environment, and muck about with the code, cd to
the top folder and run:

```bash
> pip intall --editable .
```
This will install the app, called manage, and it's dependencies.

<h2>Distribution</h2>

If you pull this from the git repo, you will have two folders in the top level
folder that contain the actual model, and it's templates:

- json: This folder contains the primary model file: `model.json`, as well
as the `default_roles.json` file.  More on this later.

- policy_templates: This folder contains the current set of policy templates. The
templates use jinja2, and get passed the region, env, role, and service variables
from the model.


<h2>The Model</h2>

<h3>Roles</h3>
In the confyrm model, IAM roles are named using the pattern `<region>-<env>-<role>`
where:
- region is an AWS region, such as us-west-2
- env is a Confyrm hosted environment, such as
 - prod
 - qa
 - test
 - dev
 - infra
 - corp
- role is the principle role for the instance.

Thus, we have roles named things like:
- us-west-2-prod-api_nginx
- us-west-2-corp-kibana
- us-west-2-infra-jenkins

You get the idea.

<h3>Role Policies</h3>

Policies follow a similar naming pattern, with a slight twist.  Policy names
follow the pattern `<region>-<env>-<service>` due to the fact that a single role
may have multiple services, and require multiple policies.

<h3>Model Template</h3>
The model template is a json structure as follows:

```json
[
  {
    "<region>":{
      "<env>":{
        "<role>":{
          "<service>":["<template>"]
        }
      }
    }
  }
]
```
Each item in the list of templates (per service) are processed by jinja2, with
values of the containing region, env, role, and service.  This becomes the
policy document that is given to AWS IAM.  Because of the ease with which this
model allows you to specify policies, this enables you to have very fine grained
policies, rather than monolithic policies per role.

<h2>Manaage app</h2>
The manage app has two primary commands:

- policies: Creates, compares, and updates policies based on the model

- roles: Creates, compares, and updates AWS roles based on the model. Including
attaching policies.
