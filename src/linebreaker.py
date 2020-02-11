import praw
from prawcore.exceptions import Forbidden
from prawcore.exceptions import ServerError
from prawcore.exceptions import RequestException
from time import sleep
from datetime import datetime
import json
from os import listdir
from os.path import isfile, join
import re

COMMENT_MAX = 10000
WORDS_PER_PARAGRAPH = 125
punctuation_list = ['.','!','?']

bot_reply = "Hey {}, it looks like you posted a wall of text. I have separated it into paragraphs for you!"
bot_author = "This bot is maintained by /u/otiskingofbidness. Please let me know if you encounter any issues with it :)"
opt_out = "_Send a private message with title **'opt out'** to prevent this bot from seeing your posts in the future._"
stats = 'r/{} has contributed {}% of all walls of text analyzed so far!'
opt_in = "Sorry! I wont bother you any further! Please message /u/otiskingofbidness if youd like to opt back in at any point!"

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
        if (iter % WORDS_PER_PARAGRAPH) == 0:
            if pflag: #punctuation is present
                punc_count = 0

                for punc in punctuation_list: #determine if current word contains punctuation.
                    punc_count += word.find(punc)

                if punc_count > (-len(punctuation_list)): #word contains punctuation
                    npars += 1
                    new_par = True
                    iter += 1
                    #offset = 0
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
                #offset += 1 #increase offset
                punc_count = 0

                for punc in punctuation_list:
                    punc_count += word.find(punc)

                if punc_count > (-len(punctuation_list)): #word contains punctuation
                    npars += 1
                    new_par = True
                    iter += 1
                    cflag = False

    return paragraphs

def isList(str):
    l = 0
    l += len(re.compile(r'- (.*?)\n', re.M).findall(str))
    l += len(re.compile(r'\* (.*?)\n', re.M).findall(str))
    l += len(re.compile(r'[0-9]+\) (.*?)\n', re.M).findall(str))
    l += len(re.compile(r'[0-9]+\. (.*?)\n', re.M).findall(str))
    return l > 0

def isValid(str, bans, sub_name, user):
    retval = len(str.split(' ')) < 3*WORDS_PER_PARAGRAPH
    if retval == False:
        retval = retval or isList(str)
        retval = retval or ('\n' in str)
        retval = retval or ('\n\n' in str)
        retval = retval or ('  \n' in str)
        retval = retval or ('\\\n' in str)

        for sub in bans['disallowed']:
            retval = retval or (sub_name == sub)
        for sub in bans['permission']:
                retval = retval or (sub_name == sub)
        for sub in bans['posts-only']:
                retval = retval or (sub_name == sub)

        retval = retval or (sub_name == 'SocialMixer')
        retval = retval or (sub_name == 'mentalhealth')
        retval = retval or (sub_name == 'mentalillness')
        retval = retval or (sub_name == 'emotionalabuse')
        retval = retval or (sub_name == 'MentalHealthSupport')
        retval = retval or (sub_name == 'abuse')
        retval = retval or (sub_name == 'ChronicIllness')
        retval = retval or (sub_name == 'TrueOffMyChest')
        retval = retval or (sub_name == 'OffMyChest')
        retval = retval or (sub_name == 'depression_help')
        retval = retval or (sub_name[0:2] == 'u_')

        dnd = open('./do_not_disturb.txt', 'r')

        for dnd_user in dnd.readlines():
            retval = retval or (user == dnd_user.strip())

        dnd.close()

    return retval

def wallRatio(sub_name):
    path = '../data/'
    count = 0
    files = [f for f in listdir(path) if isfile(join(path, f))]

    total = len(files)

    for file in files:
        if sub_name in file:
            count += 1

    return float(count/total) * 100.0

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
reddit = praw.Reddit(user_agent='Linebreaker bot (by /u/otiskingofbidness)',
                     client_id=uid, client_secret=secret,
                     username=username, password=password)

#choose a subreddit to watch
subreddit = reddit.subreddit('all')

bottiquette = reddit.subreddit('Bottiquette').wiki['robots_txt_json']
bans = json.loads(bottiquette.content_md)

#watch submission stream of the subreddit for new submissions (starting with the 100 previous posts)
while True:
    try:
        log = open("./linebreaker-bot.log", "a+")
        for submission in subreddit.stream.submissions():
            sub_name = submission.subreddit.display_name
            inbox = reddit.inbox
            dnd_list = open("./do_not_disturb.txt", 'a+')

            try:
                for message in inbox.unread():
                    message.mark_read()
                    if message.subject.lower() == 'opt out' or message.subject.lower() == 'opt-out':
                        dnd_list.write(message.author.name + '\n')
                        message.reply(opt_in)
            except ServerError as e:
                log.write("ERROR: " + str(e) + "\n")
                if '503' in str(e):
                    sleep(30)
                    for message in inbox.unread():
                        message.mark_read()
                        if message.subject.lower() == 'opt out':
                            dnd_list.write(message.author.name + '\n')
                            message.reply(opt_in)
            except RequestException as e:
                log.write("ERROR" + str(e) + "\n")
                try:
                    dnd_list.close()
                    continue
                except:
                    continue

            dnd_list.close()

            nparts = 1 #number of messages needed to fully paragraphify
            words = submission.selftext.split(' ')

            try:
                if(submission.selftext == None) or (submission.author == None):
                    continue
            except:
                log.close()
                continue

            if isValid(submission.selftext, bans, submission.subreddit.display_name, submission.author.name):
                pass
            else:
                date_time = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
                data_file_name = "../data/{}.txt".format(sub_name + '_' + date_time)
                data_file = open(data_file_name, 'w', encoding='utf-8')
                data_file.write(submission.selftext)
                data_file.close()

                blocks = paragraphify(submission.selftext) #list of paragraphs created
                if len(blocks) == 1:
                    continue

                reply_str = ''
                for block in blocks: #create new reply string using created paragraphs and adding linebreaks
                    reply_str += block + '\n\n&nbsp;\n\n'
                    if (len(reply_str + block)) >= (COMMENT_MAX-500): #adding a paragraph will exceed character limit
                        reply_str = 'PART {}\n\n&nbsp;\n\n'.format(nparts) + reply_str #add PART header
                        try: #try to post a comment
                            submission.reply(reply_str)
                            reply_str = ''
                            nparts += 1
                        except praw.exceptions.APIException as e: #usually a rate limit exception. wait 10 seconds and try again
                            sleep(10)
                            submission.reply(reply_str)
                            reply_str = ''
                            nparts += 1
                            log.write("ERROR: " + str(e) + "\n")
                        except Forbidden as e:
                            log.write("ERROR: " + str(e) + "\n")
                            continue


                reply_str += bot_reply.format('/u/' + submission.author.name) + '\n\n' + '\n\n' + \
                             opt_out + '\n\n' + stats.format(sub_name, round(wallRatio(sub_name),2))

                if(nparts > 1):
                    reply_str = 'PART {}\n\n&nbsp;\n\n'.format(nparts) + reply_str

                try: #add final comment
                    submission.reply(reply_str)
                except praw.exceptions.APIException as e:
                    sleep(10)
                    submission.reply(reply_str)
                    log.write("ERROR: " + str(e) + "\n")
                except Forbidden as e:
                    log.write("ERROR: " + str(e) + "\n")
                    continue

        log.close()
    except ServerError as e:
        try:
            log.close()
        except:
            pass
        log.write('ERROR: ' + str(e))
        continue
    except Forbidden as e:
        try:
            log.close()
        except:
            pass
        continue