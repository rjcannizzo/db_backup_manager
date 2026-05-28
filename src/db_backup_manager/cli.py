import typer

app = typer.Typer()

@app.command()
def main():
    typer.echo("db-backup-manager")

if __name__ == "__main__":
    app()