from .command import init,upload,delete,gen,ls,cli

cli.add_command(init)
cli.add_command(upload)
cli.add_command(delete)
cli.add_command(gen)
cli.add_command(ls)

__all__ = [
    'cli'
]