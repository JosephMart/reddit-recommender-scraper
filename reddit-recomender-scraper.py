import os
import io
import re
import logging
import sys
import time
import datetime

import praw
import click
from multiprocessing import Pool as ThreadPool
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(filename='app.log', level=logging.INFO)
regex_subreddit = re.compile(r'\bhttps:\/\/www\.reddit\.com\/r\/\s*([^\n\r]*)/')
reddit_instance = praw.Reddit(client_id=os.environ['client_id'],
                              client_secret=os.environ['client_secret'],
                              username=os.environ['username'],
                              password=os.environ['password'],
                              user_agent='Fetching data for subreddit recomendations',
                              api_request_delay=2)


@click.group()
def cli():
    pass


def wait_until(execute_it_now):
    while True:
        diff = (execute_it_now - datetime.datetime.now()).total_seconds()
        if diff <= 0:
            return
        elif diff <= 0.1:
            time.sleep(0.001)
        elif diff <= 0.5:
            time.sleep(0.01)
        elif diff <= 1.5:
            time.sleep(0.1)
        else:
            time.sleep(1)


@click.command()
@click.option('--file', type=click.File('r'))
def setup(file: io.TextIOWrapper):
    logging.info('Setup starting')
    try:
        with open('cleanSubreddits.txt', 'w') as out:
            calls_this_min = 0
            oldtime = time.time()

            for line in file:
                if time.time() - oldtime > 59:
                    calls_this_min = 0
                    oldtime = time.time()
                elif calls_this_min >= 60:
                    logging.info('waiting...')
                    wait_until(datetime.datetime.fromtimestamp(oldtime + 60))
                    calls_this_min = 0
                    oldtime = time.time()

                x = regex_subreddit.findall(line)
                if len(x) != 1:
                    logging.error(f'Error with {line}')
                    continue

                try:
                    calls_this_min += 1
                    subscribers = reddit_instance.subreddit(x[0]).subscribers
                except Exception as e:
                    logging.error(f'Error with {line}')
                    continue
                logging.info(f'{x[0]}-{subscribers}')
                out.write(f'{x[0]}-{subscribers}\n')

    except KeyboardInterrupt:
        logging.info('Keyboard interupt')
        sys.exit(1)


@click.command()
@click.option('--file', type=click.File('r'))
@click.option('--filefilter', type=click.File('r'))
def filter(file: io.TextIOWrapper, filefilter: io.TextIOWrapper):
    filterList = []
    for l in filefilter:
        try:
            filterList.append(regex_subreddit.findall(l)[0])
        except:
            continue

    result = []
    for l in file:
        if l not in filterList:
            result.append(l)

    with open('filterSubreddits.txt', 'w') as out:
        out.writelines(result)


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
cli.add_command(filter)

if __name__ == "__main__":
    cli()
