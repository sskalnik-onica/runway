# Runway

## What?
A lightweight wrapper around linting (e.g. yamllint) & infrastructure deployment tools (e.g. CloudFormation, Terraform, Serverless) to ease management of per-environment configs & deployment.

## Why?
Very simple configuration to:

* Perform automatic linting/verification
* Ensure deployments are only performed when an environment config is present
* Define an IAM role to assume for each deployment
* Wrangle Terraform backend/workspace configs w/ per-environment tfvars
* Avoid long-term tool lock-in
    * runway is a simple wrapper around standard tools. It simply helps to avoid convoluted Makefiles / CI jobs

## How?

### Basic Concepts

* Modules:
    * A single-tool configuration of an application/component/infrastructure (e.g. a set of CloudFormation stacks to deploy a VPC, a Serverless app)
* Regions:
    * AWS regions
* Environments:
    * A Serverless stage, a Terraform workspace, etc.
    * Environments are determined automatically from:
        1. Git branches. We recommend promoting changes through clear environment branches (prefixed with `ENV-`). For example, when running a deployment in the `ENV-dev` branch `dev` will be the environment. The `master` branch can also be used as a special 'shared' environment called `common` (e.g. for modules not normally promoted through other environments).
        2. The parent folder name of each module. For teams with a preference or technical requirement to not use git branches, each environment can be represented on disk as a folder. Instead of promoting changes via git merges, changes can be promoted by copying the files between the environment folders. See the `ignore_git_branch` runway.yml config option.
        3. The `DEPLOY_ENVIRONMENT` environment variable.
* Deployments:
    * Mappings of modules to regions, optionally with AWS IAM roles to assume
* runway.yml:
    * List of deployments
    * When the `CI` environment variable is set, all deployments are run in order; otherwise, the user is prompted for deployments to run.

### Repo Structure

Sample repo structure, showing 2 modules using environment git branches (these same files would be present in each environment branch, with changes to any environment promoted through branches):
```
.
├── myapp.cfn
│   ├── dev-us-west-2.env
│   ├── prod-us-west-2.env
│   ├── myapp.yaml
│   └── templates
│       └── foo.json
├── myapp.tf
│   ├── backend.tfvars
│   ├── dev-us-east-1.tfvars
│   ├── prod-us-east-1.tfvars
│   └── main.tf
└── runway.yml
```

Another sample repo structure, showing the same modules nested in environment folders:
```
.
├── dev
│   ├── myapp.cfn
│   │   ├── dev-us-west-2.env
│   │   ├── myapp.yaml
│   │   └── templates
│   │       └── myapp_cf_template.json
│   ├── myapp.tf
│   │   ├── backend.tfvars
│   │   ├── dev-us-east-1.tfvars
│   │   └── main.tf
│   └── runway.yml
└── prod
    ├── myapp.cfn
    │   ├── prod-us-west-2.env
    │   ├── myapp.yaml
    │   └── templates
    │       └── myapp_cf_template.json
    ├── myapp.tf
    │   ├── backend.tfvars
    │   ├── prod-us-east-1.tfvars
    │   └── main.tf
    └── runway.yml
```

### Runway Config File

runway.yml example:
```
---
# Order that modules will be deployed. A module will be skipped if a
# corresponding env/config file is not present in its directory.
# (e.g., for cfn modules, if a dev-us-west-2.env file is not in the 'app.cfn'
# directory when running a dev deployment of 'app' to us-west-2 then it will be
# skipped.)
deployments:
  - modules:
      - myapp.cfn
    regions:
      - us-west-2
  - modules:
      - myapp.tf
    regions:
      - us-east-1
    assume-role:
      # When running multiple deployments, post_deploy_env_revert can be used
      # to revert the AWS credentials in the environment to their previous
      # values
      # post_deploy_env_revert: true
      arn: arn:aws:iam::account-id:role/role-name

# If using environment folders instead of git branches, git branch lookup can
# be disabled entirely (see "Repo Structure")
# ignore_git_branch: true
```

runway.yml can also be placed in a module directory (e.g. a repo/environment containing only one module doesn't need to nest the module in a subdirectory):
```
---
# This will deploy the module in which runway.yml is located
deployments:
  - current_dir: true
    regions:
      - us-west-2
    assume-role:
      arn: arn:aws:iam::account-id:role/role-name
```

## Installation
* Install Python 2
    * On Linux:
        * `sudo apt-get -y install python-pip python-minimal`
        * `echo 'export PATH=$HOME/.local/bin:$PATH' >> ${HOME}/.bashrc`
        * `source ${HOME}/.bashrc`
    * On macOS:
        * `if ! which pip > /dev/null; then easy_install --user pip; fi`
        * `echo 'export PATH="${HOME}/Library/Python/2.7/bin:${PATH}"' >> ${HOME}/.bash_profile`
        * `source ${HOME}/.${SHELL_NAME}_profile`
* Install runway:
    * `pip install --user runway`

## Use
* `runway test` (aka `runway preflight`)  - execute this in your environment to catch errors; if it exits `0`, you're ready for...
* `runway plan`  (aka `runway taxi`) - this optional step will show the diff/plan of what will be changed. With a satisfactory plan you can...
* `runway deploy` (aka `runway takeoff`) - if running interactively, you can choose which deployment to run; otherwise (i.e. on your CI system) each deployment will be run in sequence.

## Module Configurations

### CloudFormation

CloudFormation modules are managed by 2 files: a key/value environment file, and a yaml file defining the stacks/templates/params.

Environment - name these in the form of env-region.env (e.g. dev-contoso.env):
```
# Namespace is used as each stack's prefix
# We recommend an (org/customer)/environment delineation
namespace: contoso-dev
environment: dev
customer: contoso
region: us-west-2
# The stacker bucket is the S3 bucket (automatically created) where templates
# are uploaded for deployment (a CloudFormation requirement for large templates)
stacker_bucket_name: stacker-contoso-us-west-2
```

Stack config - these can have any name ending in .yaml (they will be evaluated in alphabetical order):
```
# Note namespace/stacker_bucket_name being substituted from the environment
namespace: ${namespace}
stacker_bucket: ${stacker_bucket_name}

stacks:
  myvpcstack:  # will be deployed as contoso-dev-myvpcstack
    template_path: templates/vpc.yaml
    # The enabled option is optional and defaults to true. You can use it to
    # enable/disable stacks per-environment (i.e. like the namespace
    # substitution above, but with the value of either true or false for the
    # enabled option here)
    enabled: true
  myvpcendpoint:
    template_path: templates/vpcendpoint.yaml
    # variables map directly to CFN parameters; here used to supply the
    # VpcId output from the myvpcstack to the VpcId parameter of this stack
    variables:
      VpcId: ${output myvpcstack::VpcId}
```

### Serverless

Standard [Serverless](https://serverless.com/framework/) rules apply, with the following recommendations/caveats:

* Runway environments map directly to Serverless stages.
* A `package.json` file is required, specifying the serverless dependency and a deploy script, e.g.:
```
{
  "name": "mymodulename",
  "version": "1.0.0",
  "description": "My serverless module",
  "main": "handler.py",
  "devDependencies": {
    "serverless": "^1.25.0"
  },
  "scripts": {
    "deploy": "sls deploy"
  },
  "author": "Serverless Devs",
  "license": "ISC"
}
```
* We strongly recommend you commit the package-lock.json that is generated after running `npm install`
* Each stage requires its own config file (even if empty for a particular stage), in one of the following forms:
```
config-STAGE-REGION.yaml
config-STAGE.yaml
config-STAGE-REGION.yml
config-STAGE.yml
config-STAGE-REGION.json
config-STAGE.json
```

### Terraform

Standard Terraform rules apply, with the following recommendations/caveats:

* Each environment requires its own tfvars file, in the form of ENV-REGION.tfvars (e.g. dev-contoso.tfvars).
* We recommend having a backend configuration separate from the terraform module code:

main.tf:
```
terraform {
  backend "s3" {
    key = "some_unique_identifier_for_my_module" # e.g. contosovpc
  }
}
# continue with code here...
```
backend.tfvars (or backend-ENV-REGION.tfvars, or backend-ENV.tfvars, or backend-REGION.tfvars):
```
bucket = "SOMEBUCKNAME"
region = "SOMEREGION"
dynamodb_table = "SOMETABLENAME"
```
