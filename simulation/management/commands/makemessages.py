"""Include pure-core message templates in Django's standard gettext workflow."""

from django.core.management.commands.makemessages import Command as DjangoCommand


class Command(DjangoCommand):
    xgettext_options = [*DjangoCommand.xgettext_options, "--keyword=message", "--keyword=Message"]
