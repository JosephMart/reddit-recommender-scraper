import os
import io
import re

import praw
import click
from multiprocessing import Pool as ThreadPool
from dotenv import load_dotenv

load_dotenv()

regex_subreddit = re.compile(r'\bhttps:\/\/www\.reddit\.com\/r\/\s*([^\n\r]*)/')
reddit_instance = praw.Reddit(client_id=os.environ['client_id'],
                      client_secret=os.environ['client_secret'],
                      username=os.environ['username'],
                      password=os.environ['password'],
                      user_agent='Fetching data for subreddit recomendations')


@click.group()
def cli():
    pass

def setupRunner(line: str):
    x = regex_subreddit.findall(line)

    if len(x) != 1:
        print(f'Error with {line}', end='')
        return '', 0

    try:
        subscribers = reddit_instance.subreddit(x[0]).subscribers
    except:
        print(f'Error with {line}', end='')
        return x[0], 0
    return x[0], subscribers

@click.command()
@click.option('--file', type=click.File('r'))
@click.option('--workers', default=5, type=int)
def setup(file: io.TextIOWrapper, workers: int):
    pool = ThreadPool(workers)
    results = pool.map(setupRunner, file)

    # close the pool and wait for the work to finish
    pool.close()
    pool.join()

    with open('cleanSubreddits.txt', 'w') as out:
        results.sort(key=lambda tup: tup[1], reverse=True)
        for r in results:
            out.write(f'{r[0]}\n')

@click.command()
@click.option('--file', type=click.File('r'))
@click.option('--workers', default=5, type=int)
def run(file: io.TextIOWrapper, workers: int):
    def runner(subreddit_url: str):
        x = regex_subreddit.findall(subreddit_url)

        if len(x) != 1:
            print(f'Error with {subreddit_url}')
            return ''

        s = reddit_instance.subreddit(x[0])
        return s.subscribers

    pool = ThreadPool(workers)
    results = pool.map(runner, file)

    # close the pool and wait for the work to finish
    pool.close()
    pool.join()

    with open('done.txt', 'w') as out:
        for r in results:
            out.write(f'{r}\n')


cli.add_command(run)
cli.add_command(setup)

if __name__ == "__main__":
    cli()
