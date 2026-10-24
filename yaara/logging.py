"""Keep private invitation credentials out of application request diagnostics."""

import logging
import re

INVITATION_PATH = re.compile(r"(/join/)[^/\s?#\"'<>]+")


def redact_invitations(value):
    return INVITATION_PATH.sub(r"\1[redacted]", value)


class PrivateInvitationFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact_invitations(record.getMessage())
        record.args = ()
        if record.exc_info:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
            record.exc_info = None
        if record.exc_text:
            record.exc_text = redact_invitations(record.exc_text)
        if record.stack_info:
            record.stack_info = redact_invitations(record.stack_info)
        return True
