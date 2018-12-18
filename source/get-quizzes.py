import getopt
import html
import json
import requests
import sys
import os.path
from datetime import datetime

class QuizDataSet:
    def __init__(self):
        self.ids = set()
        self.titles = []
        self.latest_date = datetime.min
        self.all_metadata = []

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "s:e:m:r", ["start=","end=","maximum="])
    except getopt.GetoptError:
        print("get-quizzes.py -s <start_page> -e <end_page> -m <maximum_pages> -r")
        sys.exit(2)

    start_page = 1
    end_page = -1
    max_pages = -1
    reset = False
    for opt, arg in opts:
        if opt == "-s":
            start_page = int(arg)
        elif opt == "-e":
            end_page = int(arg)
        elif opt == "-m":
            max_pages = int(arg)
        elif opt == "-r":
            reset = True

    print("Getting quizzes from page %i to %s (%s) with%s reset" % \
          (start_page, \
           "end" if end_page == -1 else str(end_page), \
           "no maximum" if max_pages == -1 else "maximum " + str(max_pages), \
           "" if reset else "out"))

    if not reset:
        data = load_previous_data()
    else:
        data = QuizDataSet()
        
    load_new_data(data, start_page, end_page, max_pages)

    # prepare the text output for training the AI
    with open("output/titles.txt", "w+") as titles_file:
        for t in data.titles:
            titles_file.write("%s\n" % html.unescape(t))

    # prepare the json output for the next iteration
    with open("output/buzzfeed-quizzes.json", "w+") as json_file:
        json_file.write(json.dumps(data.all_metadata))

def load_previous_data():
    # load the previously downloaded data
    data = QuizDataSet()
    if not os.path.isfile("output/buzzfeed-quizzes.json"):
        print("No previous data to load.")
        return data
    
    with open("output/buzzfeed-quizzes.json") as json_file:
        data.all_metadata = json.load(json_file)
        data.latest_date = datetime.min
        for q in data.all_metadata:
            quiz_date = datetime.utcfromtimestamp(int(q["published"]))
            data.ids.add(q["id"])
            if q["language"] == "en":
                data.titles.append(q["title"])
            if quiz_date > data.latest_date:
                data.latest_date = quiz_date

    print("Previous data loaded.")
    print("Date of latest previously loaded quiz %s" % data.latest_date.isoformat())
    return data

def load_new_data(data, start_page, end_page, maximum_pages):
    # now get some new data
    url = "http://www.buzzfeed.com/api/v2/feeds/quiz?p=%i"
    i = start_page
    total_page_count = 0
    total_quiz_count = 0
    total_added = 0

    while (maximum_pages == -1 or total_page_count <= maximum_pages) and (i <= end_page or end_page == -1):
        total_page_count += 1
        response = requests.get(url % i)
        response_json = response.json()
        buzzes = response_json["buzzes"]

        # if we don't get any buzzes, we've hit the end of the pages
        if (len(buzzes) == 0):
            break

        latest_on_page = datetime.min
        for b in buzzes:
            total_quiz_count += 1;
            published_date = datetime.utcfromtimestamp(int(b["published"]))
            if published_date > latest_on_page:
                latest_on_page = published_date
            id = b["id"]
            if id in data.ids:
                continue
            data.ids.add(id)
            data.all_metadata.append(b)
            if b["language"] == "en":
                data.titles.append(b["title"])
                total_added += 1

        print("Read page %i: latest post on page %s" % (i, latest_on_page.isoformat()))
        if latest_on_page <= data.latest_date:
            break

        i += 1

    print("%i quizzes found, %i quizzes added to training set" % (total_quiz_count, total_added))

if __name__ == "__main__":
    main(sys.argv[1:])
