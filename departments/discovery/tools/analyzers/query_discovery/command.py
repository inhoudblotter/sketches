import typer
from .commands.queries import register_queries
from .commands.mutations import register_mutations

query_app = typer.Typer(
    help="Swiss army knife for the team's discovery querying and bulk mutations."
)

register_queries(query_app)
register_mutations(query_app)

command = query_app
