import praw
from time import sleep

COMMENT_MAX = 10000
WORDS_PER_PARAGRAPH = 150
punctuation_list = ['.','!','?']

bot_reply = "Hey {} looks like you posted a wall of text. I have seperated it into paragraphs for you!"
bot_author = "This bot is maintained by /u/otiskingofbidness. Please let me know if you encounter any issues with it :)"

'''
Takses a string of text and breaks it up into a list of paragraphs.
@str: the string to be broken up
'''
def paragraphify(str):
    words = str.split(' ') #string text seperated into words
    paragraphs = [] #list of paragraphs
    npars = 0 #number of paragraphs created
    iter = 1 #word iteration number (starts at 1 for modulo math)
    offset = 0 #word offset for modulo
    pcount = 0 #punctuation count
    pflag = False #punctuation flag
    cflag = False #continuation flag
    new_par = True #new paragraph flag

    #determine if wall of text contains any of the punctuation characters
    for p in punctuation_list:
        pf = p in str
        if pf:
            pcount += 1

    #pcount > 0 means punctuation characters found. assert punctuation flag
    if pcount > 0:
        pflag = True

    #iterate over the words in the wall of text
    for word in words:
        if new_par: #create a new paragraph entry in the paragraph list
            paragraphs.append('>' + word) #'>' adds quotation block on reddit
            new_par = False
        else: #append to current paragraph
            paragraphs[npars] += ' ' + word

        #this condition detects if the word iter has covered enough words to contitute a new paragraph.
        #the offset is used to make up for longer paragraphs created by contiunuing sentance boundaries.
        if (iter % WORDS_PER_PARAGRAPH) == offset:
            if pflag: #punctuation is present
                punc_count = 0

                for punc in punctuation_list: #determine if current word contains punctuation.
                    punc_count += word.find(punc)

                if punc_count > (-len(punctuation_list)): #word contains punctuation
                    npars += 1
                    new_par = True
                    iter += 1
                    offset = 0
                else: #word contains no punctuation. assert continuation flag to keep adding words to paragraph.
                    iter += 1
                    cflag = True
            else: #no punctuation detected, seperate just on word boundaries of size WORDS_PER_PARAGRAPH
                npars += 1
                new_par = True
                iter += 1
        else:
            iter += 1
            if cflag: #continuation flag asserted
                offset += 1 #increase offset
                punc_count = 0

                for punc in punctuation_list:
                    punc_count += word.find(punc)

                if punc_count > (-len(punctuation_list)): #word contains punctuation
                    npars += 1
                    new_par = True
                    iter += 1
                    cflag = False

    return paragraphs



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


#create a Reddit instance using login creditials and OAuth
reddit = praw.Reddit(user_agent='Linebreaker (by /u/otiskingofbidness)',
                     client_id=uid, client_secret=secret,
                     username=username, password=password)

#choose a subreddit to watch
subreddit = reddit.subreddit('linebreakerbot')

#watch submission stream of the subreddit for new submissions (starting with the 100 previous posts)
for submission in subreddit.stream.submissions():

    submission.comment_sort = 'new'
    comments = submission.comments.list()
    nparts = 1 #number of messages needed to fully paragraphify
    words = submission.selftext.split(' ')
    if '\n\n' in submission.selftext or (2 * WORDS_PER_PARAGRAPH) > len(words): #no need to paragraphify
        pass
    else:
        blocks = paragraphify(submission.selftext) #list of paragraphs created

        reply_str = ''
        for block in blocks: #create new reply string using created paragraphs and adding linebreaks
            reply_str += block + '\n\n&nbsp;\n\n'
            if (len(reply_str + block) + 50) > COMMENT_MAX: #adding a paragraph will exceed character limit
                reply_str = 'PART {}\n\n&nbsp;\n\n'.format(nparts) + reply_str #add PART header
                try: #try to post a comment
                    submission.reply(reply_str)
                    reply_str = ''
                    nparts += 1
                except praw.exceptions.APIException: #usually a rate limit exception. wait 10 seconds and try again
                    sleep(10)
                    submission.reply(reply_str)
                    reply_str = ''
                    nparts += 1


        reply_str += bot_reply.format('/u/' + submission.author.name) + '\n\n' + bot_author

        if(nparts > 1):
            reply_str =  'PART {}\n\n&nbsp;\n\n'.format(nparts) + reply_str

        try: #add final comment
            submission.reply(reply_str)
        except praw.exceptions.APIException:
            sleep(10)
            submission.reply(reply_str)

    #same as above but iterating over comments in a thread.
    for comment in comments:
        nparts = 1
        words = comment.body.split(' ')
        if comment.author.id == uid:
            continue

        if '\n\n' in comment.body or (2 * WORDS_PER_PARAGRAPH) > len(words):
            pass
        else:
            blocks = paragraphify(comment.body)
            reply_str = ''
            for block in blocks:
                reply_str += block + '\n\n&nbsp;\n\n'
            if (len(reply_str + block + bot_reply + bot_author) + 27) > COMMENT_MAX:
                    reply_str = 'PART {}\n\n&nbsp;\n\n'.format(nparts) + reply_str
                    try:
                        comment.reply(reply_str)
                        reply_str = ''
                        nparts += 1
                    except praw.exceptions.APIException:
                        sleep(10)
                        comment.reply(reply_str)
                        reply_str = ''
                        nparts += 1

            reply_str += bot_reply.format('/u/' + comment.author.name) + '\n\n' + bot_author

            if(nparts > 1):
                reply_str =  'PART {}\n\n&nbsp;\n\n'.format(nparts) + reply_str

            try:
                comment.reply(reply_str)
            except praw.exceptions.APIException:
                sleep(10)
                comment.reply(reply_str)