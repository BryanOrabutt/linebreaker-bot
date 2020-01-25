import praw

#Read OAuth keys and reddit login credentials from file.
try:
    fp = open('../auth/linebreaker.key', 'r')
    line = fp.readline()
    uid = line.partition(':')[2].strip()
    line = fp.readline()
    secret = line.partition(':')[2].strip()
except:
    print("Problem opening key file!")
finally:
    fp.close()

try:
    fp = open('../auth/linebreaker.login', 'r')
    line = fp.readline()
    username = line.partition(':')[2].strip()
    line = fp.readline()
    password = line.partition(':')[2].strip()
except:
    print("Problem opening login file!")
finally:
    fp.close()


reddit = praw.Reddit(user_agent='Linebreaker (by /u/otiskingofbidness)',
                     client_id=uid, client_secret=secret,
                     username=username, password=password)

subreddit = reddit.subreddit('linebreakerbot')

SUBMISSION_MAX = 40000
COMMENT_MAX = 10000
words_per_paragraph = 150
punctuation_list = ['.','!','?']

bot_reply = "Hey {} looks like you posted a wall of text. I have seperated it into paragraphs for you!"
bot_author = "This bot is maintained by /u/otiskingofbidness. Please let me know if you encounter any issues with it :)"

for submission in subreddit.stream.submissions():

    submission.comment_sort = 'new'
    comments = submission.comments.list()
    if '\n\n' in submission.selftext or (2*words_per_paragraph) > len(submission.selftext):
        print('valid submission')
        pass
    else:
        submission_pflag = False
        submission_pcount = 0

        for p in punctuation_list:
            pf = p in submission.selftext
            if pf:
                submission_pcount += 1

        if submission_pcount > 0:
            submission_pflag = True

        submission_words = submission.selftext.split(' ')

        print(submission_words)

    for comment in comments:
        if comment.author.id == uid:
            continue

        if '\n\n' in comment.body or (2*words_per_paragraph) > len(comment.body):
            print("valid comment")
            pass
        else:
            comment_pflag = False
            comment_pcount = 0

            for p in punctuation_list:
                pf = p in comment.body
                if pf:
                    comment_pcount += 1

            if comment_pcount > 0:
                comment_pflag = True

            comment_words = comment.body.split(' ')
            print(comment_words)