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
as the `properties.json` file, used for processing the model.  More on this later.

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
<h3>Processing the Model</h3>
The model file itself is processed with jinja2, in order to minimize the
amount of redundency in the model specification.  The file `properties.json` is
loaded at runtime, and used as the input to jinja2.  So, if you want to extend
the model, you can add additional data to that file.  

Along with the data in the properties.json file, the instantiated CSMContext
object is also available in the `ctx` attribute.  So, for instance, the `orgId`
attribute in the runtime `CSMContext` is available to jinja as `ctx.orgId`.

<h3>Processing the Templates</h3>

Each service listing in the model contains a set of 1 or more templates.  These
identify the template files in the `policy_templates` folder (and are named
the same, but without the `.template` extension).

Each template file is processed by jinja2.  Along with the standard properties,
and CSMContext, the values of the relevant region, env, and service
are made available to jinja2.

The processed output becomes the
policy document that is given to AWS IAM.  Because of the ease with which this
model allows you to specify policies, this enables you to have very fine grained
policies, rather than monolithic policies per role.

<h2>Manaage app</h2>
The manage app has three primary commands:

- policies: Creates, compares, and updates policies based on the model

- roles: Creates, compares, and updates AWS roles based on the model. Including
attaching policies.

- model: Show the processed model.  This will show you exactly what the final
policies look like once processed.  If you want to see the raw json model (after
processing) use the `model json` command
