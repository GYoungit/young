import requests
import time
import json

class RealParser :
    params = {
        'key': '28e650e7-f611-4e98-a5ac-4f481f77922f',
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    def getParsingTag(self, text) :
        count = 0
        self.params['text'] = text

        while True :
            if count > 5 :
                break
            try:
                parsingData = requests.post(url="http://iip.hanbat.ac.kr/RealParser/parsingApi",
                                            data=self.params, headers=self.headers).text
                count += 1
                break
            except:
                time.sleep(2)
                continue

        parsingData = json.loads(parsingData)
        return parsingData


    def getParsingLSU(self, text):
        count = 0
        self.params['text'] = text

        while True:
            if count > 5:
                break
            try:
                parsingData = requests.post(url="http://iip.hanbat.ac.kr/RealParser/parsingLSU",
                                            data=self.params, headers=self.headers).text
                count += 1
                break
            except:
                time.sleep(2)
                continue

        return parsingData


    def getParsingWord(self, text):
        count = 0
        self.params['text'] = text

        while True:
            if count > 5:
                break
            try:
                parsingData = requests.post(url="http://iip.hanbat.ac.kr/RealParser/parsing",
                                            data=self.params, headers=self.headers).text
                count += 1
                break
            except:
                time.sleep(2)
                continue

        return parsingData