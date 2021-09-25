from mrrc.command import init,upload,delete,gen,ls,cli
from mrrc.logs import set_logging
import logging

# override this however you want
set_logging(level=logging.INFO)

# init group command
cli.add_command(init)
cli.add_command(upload)
cli.add_command(delete)
cli.add_command(gen)
cli.add_command(ls)

__all__ = [
    'cli'
]