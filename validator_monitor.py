# -*- coding: utf8 -*-

# monitor validator's commit activity & alert by telegram message
# by dlguddus(B-Harvest)

import time
import requests
import json
import os
import threading
import sys
import datetime
from flask import Flask
from flask import Markup
from flask import Flask
from flask import render_template

validator_address = "" # put your validator node_id here
telegram_token = "" # put your telegram bot token here
telegram_chat_id = "" # put your telegram chat_id here
node_IP_port = [] # put your node's IP:port(26657) for getting node info
commit_history_period = [1, 10, 50, 100, 500, 1000, 2000, 3000, 4000, 5000, 10000, 15000, 20000] # put array of number of blocks for showing recent n-block commiting status
httpAddress = "" # http://ip:port to request gaia information

height_before = -1
height = 0
validator_height = 0
validator_timestamp = ""
count = 0
n_peers = []

app = Flask(__name__)
@app.route("/")

def flask_view():

    if height - validator_height <= 3:
        commit_status = "OK"
    else:
        commit_status = "Missing!"

    try:
        with open("commitHistory.txt") as f:
            commitHistory = json.load(f)
    except:
        commitHistory = []

    len_commitHistory = len(commitHistory)
    sumCommitArray = []
    datetimeArray = []
    blockheightArray = []
    cnt = 0

    # get recent missing commits
    for i in range(0, len_commitHistory):
        if cnt > 19 :
            break
        else :
            if commitHistory[len_commitHistory-i-1]['commit'] == "0" :
                datetimeArray.append(commitHistory[len_commitHistory-i-1]['datetime'])
                blockheightArray.append(commitHistory[len_commitHistory-i-1]['commit_height'])
                cnt = cnt + 1

    # get period missing data
    for blockPeriod in commit_history_period:
        if blockPeriod < len_commitHistory:
            sumCommit = 0
            for i in range(0,blockPeriod):
                sumCommit = sumCommit + int(commitHistory[len_commitHistory-i-1]['commit'])
            sumCommitArray.append(sumCommit)
        else:
            sumCommitArray.append(0)

    reternscript = '<meta http-equiv="refresh" content="30"><font size=1 >'
    reternscript = reternscript + 'height : ' + str(height) + '</br>validator height : ' + str(validator_height) + '</br>'
    reternscript = reternscript + 'commit status : ' + str(commit_status) + '</br></br>'
    for i in range(0,len(n_peers)):
        reternscript = reternscript + 'n_peers(' + str(i) +') : ' + str(n_peers[i]) + '</br>'

    if len(sumCommitArray)==len(commit_history_period) and len_commitHistory>0:
        num = 0
        reternscript = reternscript + '</br>missing commits / total commits (missing rate) : </br>'
        for blockPeriod in commit_history_period:
            if blockPeriod < len_commitHistory:
                reternscript = reternscript + str(blockPeriod-sumCommitArray[num]) + '/' + str(blockPeriod) + '(' + str(int((1-sumCommitArray[num]/blockPeriod)*1000.0)/10.0) + '%) '
            num = num + 1

    reternscript = reternscript + '</br></br>recent missings</br>'

    if len(datetimeArray)>0:
        for i in range(0,len(datetimeArray)):
            reternscript = reternscript + str(datetimeArray[i]) + ' --> block ' + str(blockheightArray[i]) + '</br>'

    reternscript = reternscript + '</font>'

    return reternscript

def append_to_json(_dict,path):
    with open(path, 'ab+') as f:
        f.seek(0,2)                                #Go to the end of file
        if f.tell() == 0 :                         #Check if file is empty
            f.write(json.dumps([_dict]).encode())  #If empty, write an array
        else :
            f.seek(-1,2)
            f.truncate()                           #Remove the last character, open the array
            f.write(' ,\n'.encode())                #Write the separator
            f.write(json.dumps(_dict).encode())    #Dump the dictionary
            f.write(']'.encode())

def get_data():

    global height
    global height_before
    global round
    global step
    global validator_data
    global validator_address
    global validator_height
    global validator_timestamp
    global count
    global n_peers

    while True:

        utc_datetime = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")



        try:

            # get consensus state from seednode
            Response_ConsensusState = requests.get(httpAddress + "/consensus_state", timeout=10)
            if str(Response_ConsensusState) == "<Response [200]>" :
                JSON_ConsensusState = json.loads(Response_ConsensusState.text)
                height_round_step = JSON_ConsensusState["result"]["round_state"]["height/round/step"]
                height_round_step_split = height_round_step.split("/")
                height = int(height_round_step_split[0])
                round = int(height_round_step_split[1])
                step = int(height_round_step_split[2])

                if height_before < height:
                    # get validator's commit
                    Response_CommitHeight = requests.get(httpAddress + "/commit?height=" + str(height-2), timeout=10)
                    validator_data = ""
                    if str(Response_CommitHeight) == "<Response [200]>" :
                        JSON_CommitHeight = json.loads(Response_CommitHeight.text)
                        for item in JSON_CommitHeight["result"]["SignedHeader"]["commit"]["precommits"] :
                            if str(item) == "null" or item == None : pass
                            else :
                                if item["validator_address"] == validator_address :
                                    validator_data = item
                                    validator_height = int(validator_data["height"])
                                    validator_timestamp = str(validator_data["timestamp"])
                                    break
                    else :
                        break

                    # send telegram message when missing commits
                    if validator_data == "" :
                        commitFlag = 0
                        requestURL = "https://api.telegram.org/bot" + str(telegram_token) + "/sendMessage?chat_id=" + telegram_chat_id + "&text="
                        requestURL = requestURL + str(utc_datetime) + ':MissingCommits!!!'
                        response = requests.get(requestURL, timeout=10)
                    else :
                        commitFlag = 1
                    height_before = height

                    # get n_peers for each nodes
                    n_peers = []
                    for i in range(0,len(node_IP_port)):
                        response = requests.get("http://" + str(node_IP_port[i]) + "/net_info", timeout=10)
                        n_peers.append(int(json.loads(response.text)["result"]["n_peers"]))

                    # send message in every 1 hour
                    if count > 720:
                        requestURL = "https://api.telegram.org/bot" + str(telegram_token) + "/sendMessage?chat_id=" + telegram_chat_id + "&text="
                        requestURL = requestURL + str(utc_datetime) + ':Height=' + str(height) +'/Status:OK/Peers:'
                        for i in range(0,len(n_peers)):
                            requestURL = requestURL + str(n_peers[i]) + '.'
                        response = requests.get(requestURL, timeout=10)
                        count = 0

                    count = count + 1

                    # logging data to file
                    logJSON = {'datetime':str(utc_datetime), 'block_height':str(height), 'commit_height':str(validator_height), 'commit':str(commitFlag)}
                    append_to_json(logJSON, "commitHistory.txt")

            else :
                requestURL = "https://api.telegram.org/bot" + str(telegram_token) + "/sendMessage?chat_id=" + telegram_chat_id + "&text="
                requestURL = requestURL + str(utc_datetime) + ':RequestError!!!'
                response = requests.get(requestURL, timeout=10)

            #time.sleep(1)

        except:
            requestURL = "https://api.telegram.org/bot" + str(telegram_token) + "/sendMessage?chat_id=" + telegram_chat_id + "&text="
            requestURL = requestURL + str(utc_datetime) + ':RequestError!!!'
            response = requests.get(requestURL, timeout=10)
            #time.sleep(1)


def flask_run():
    app.run(host='0.0.0.0', port='5000')

t1 = threading.Thread(name='flask_run', target=flask_run)
t2 = threading.Thread(name='get_data', target=get_data)

t1.start()
t2.start()
