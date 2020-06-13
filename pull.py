import urllib2
#from newspaper import Article
import schedule
import time

def job():
    url = "http://drneato.com/Bday/Data.txt"
    data = urllib2.urlopen(url)
   #article.download()
    #article.parse()
    #article.nlp()
    #data = article.text
    #print(data)
    file = open("Data.txt", "w")
    # for line in data:
    #     file.write(line)
    with file:
        for line in data:
            file.write(line)

schedule.every().day.at("00:00").do(job)
job()
while(True):
    schedule.run_pending()
    time.sleep(1)
