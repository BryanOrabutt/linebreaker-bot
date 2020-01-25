import praw
import glob

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
    fp.close();

print("Credentials")
print()
print("id: %s\nsecret: %s\nusername: %s\npassword: %s"%(uid, secret, username, password))
