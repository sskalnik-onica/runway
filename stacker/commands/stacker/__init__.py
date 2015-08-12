import copy

from .build import Build
from ..base import BaseCommand
from ...context import Context
from ...providers import aws


class Stacker(BaseCommand):

    name = 'stacker'
    subcommands = (Build,)

    def configure(self, options, **kwargs):
        super(Stacker, self).configure(options, **kwargs)
        options.provider = aws.Provider(region=options.region)
        options.context = Context(
            namespace=options.namespace,
            environment=options.environment,
            parameters=copy.deepcopy(options.parameters),
            stack_names=options.stacks,
            force_stacks=options.force,
        )
        options.context.load_config(options.config.read())