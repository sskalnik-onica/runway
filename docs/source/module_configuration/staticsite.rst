.. _mod-staticsite:

Static Site
===========

This module type performs idempotent deployments of static websites. It
combines CloudFormation stacks (for S3 buckets & CloudFront Distribution) with
additional logic to build & sync the sites.

It can be used with a configuration like the following::

    deployments:
      - modules:
          - path: web
            class_path: runway.module.staticsite.StaticSite
            environments:
              dev:
                namespace: contoso-dev
                staticsite_aliases: web.example.com,foo.web.example.com
                staticsite_acmcert_arn: arn:aws:acm:us-east-1:123456789012:certificate/...
            options:
              build_steps:
                - npm ci
                - npm run build
              build_output: dist
        regions:
          - us-west-2

This will build the website in ``web`` via the specified build_steps and then
upload the contents of ``web/dist`` to an S3 bucket created in the
CloudFormation stack ``web-dev-conduit``. On subsequent deploys, the website
will be built and synced only if the non-git-ignored files in ``web`` change.

The site domain name is available via the ``CFDistributionDomainName`` output
of the ``<namespace>-<path>`` stack (e.g. ``contoso-dev-web`` above) and will
be displayed on stack creation/updates.

A start-to-finish example walkthrough is available
in the :ref:`Conduit quickstart<qs-conduit>`.


.. _staticsite-config-options:

Example of all Static Site Options
----------------------------------

Most of these options are not required, but are listed here for reference::

    deployments:
      - modules:
          - name: conduitsite  # defaults to path; used in stack names & ssm parameter
            path: web
            class_path: runway.module.staticsite.StaticSite
            environments:
              # The only required environment value is namespace
              dev:
                namespace: contoso-dev
                staticsite_acmcert_arn: arn:aws:acm:us-east-1:123456789012:certificate/...

                # A cert ARN can also be looked up dynamically via SSM
                staticsite_acmcert_ssm_param: us-west-2@MySSMParamName...

                staticsite_aliases: example.com,foo.example.com
                staticsite_web_acl: arn:aws:waf::123456789012:webacl/...

                # staticsite_enable_cf_logging defaults to true
                staticsite_enable_cf_logging: true

                # Deploy Lambda@Edge to rewrite directory indexes
                # e.g. support accessing example.org/foo/
                staticsite_rewrite_directory_index: index.html

                # You can also deploy custom Lambda@Edge associations with your
                # pre-built function versions
                # (this takes precedence over staticsite_rewrite_directory_index)
                staticsite_lambda_function_associations:
                  - type: origin-request
                    arn: arn:aws:lambda:us-east-1:123456789012:function:foo:1

                # Custom error response options can be defined
                staticsite_custom_error_responses:
                  - ErrorCode: 404
                    ResponseCode: 200
                    ResponsePagePath: /index.html
            options:
              pre_build_steps:  # commands to run before generating hash of files
                - command: npm ci
                  cwd: ../myothermodule  # directory relative to top-level path setting
                - command: npm run export
                  cwd: ../myothermodule
              source_hashing:  # overrides for source hash collection/tracking
                enabled: true  # if false, build & upload will occur on every deploy
                parameter: /${namespace}/myparam  # defaults to <namespace>-<name/path>-hash
                directories:  # overrides default hash directory of top-level path setting
                  - path: ./
                  - path: ../common
                    # Additional (gitignore-format) exclusions to hashing
                    # (.gitignore files are loaded automatically)
                    exclusions:
                      - foo/*
              build_steps:
                - npm ci
                - npm run build
              build_output: dist  # overrides default directory of top-level path setting
        regions:
          - us-west-2
