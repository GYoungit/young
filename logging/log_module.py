import logging
import logging.handlers
import time
from datetime import datetime
import re
import os


def Log(filename=None) :
    fileMaxByte = 1000 * 1024 * 1024
    location = os.getcwd().split("\\")
    location = location[location.index("Pycharm"):]
    locationString = " > ".join(location)

    #시간
    t = time.strftime("%B %dth, %Y (%A) %H:%M:%S")

    # formatter 생성
    # formatter = logging.Formatter("%(levelname)s--" + t + " / %(filename)s : %(lineno)s >>> %(message)s")
    formatter = logging.Formatter('[%(levelname)s - ' + locationString + " > " + '%(filename)s:%(lineno)s] %(asctime)s > %(message)s')

    # filename setting
    if filename == None:
        date_string = str(datetime.now())
        date_string = re.sub("\..*", "", date_string).replace(" ", "_").replace(":", "")
        filename = date_string

    # log setting
    logger = logging.getLogger('mylogger')

    # fileHandler와 StreamHandler를 생성
    fileHandler = logging.handlers.RotatingFileHandler(filename + ".log", maxBytes=fileMaxByte, backupCount=10, encoding='utf-8')
    streamHandler = logging.StreamHandler()


    # Handler에 Formmater 셋팅
    fileHandler.setFormatter(formatter)
    streamHandler.setFormatter(formatter)

    # Handler를 logging에 추가
    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)

    logger.setLevel(logging.DEBUG)

    return logger
