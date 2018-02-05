import requests
import time
import json
from urllib.parse import quote





class RealParser :
    params = {
        'key': '28e650e7-f611-4e98-a5ac-4f481f77922f',
    }

    def getParsingTag(self, text) :
        textList = text.split(".")
        parsingList = []

        for i in range(len(textList) - 1) :
            textList[i] += "."

        for text in textList :
            if text.strip() == "" : continue
            while True :
                try:
                    parsingData = requests.post(url="http://iip.hanbat.ac.kr/RealParser/parsingApi?text=" + quote(text),
                                                data=self.params)
                except:
                    time.sleep(2)
                    continue
                parsingList.append(parsingData.json())
                break

        parsingJsonData = parsingList[0]

        for i in range(1, len(parsingList)) :
            i_json = parsingList[i]
            parsingJsonData['total_count'] += i_json.get('total_count')
            pjList = parsingJsonData.get("result_list")
            pjList.extend(i_json.get("result_list"))

        return parsingJsonData


    def getParsingLSU(self, text, isNone=False):
        while True :
            try:
                parsingData = requests.post(url="http://iip.hanbat.ac.kr/RealParser/parsingLSU?text=" + quote(text),
                                            data=self.params)
            except:
                time.sleep(2)
                continue
            parsingData = parsingData.text.strip()

            if isNone and parsingData == "" :
                print("parsing results is None !!!")
                continue

            break

        return parsingData


    def getParsingWord(self, text):
        textList = text.split(".")
        textList = [i for i in textList if i != ""]
        resultsList = ""

        for t in textList :
            while True :
                try:
                    parsingData = requests.post(url="http://iip.hanbat.ac.kr/RealParser/parsing?text=" + quote(t),
                                                data=self.params)
                except:
                    time.sleep(2)
                    continue
                resultsList += parsingData.text.strip()
                break

        return resultsList