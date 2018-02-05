import re
import nltk
from nltk.tokenize import RegexpTokenizer
from stop_words import get_stop_words
from nltk.stem.porter import PorterStemmer


# 생성 후 wordToPhrasalVerb 함수 사용

class PhrasalVerb :
    pattern = []

    def __init__(self, patternRoute="D:/Resilio Sync/young/Pycharm/Amazon/PhrasalVerbDict/pattern.pd",
                 synonymRoute="D:/Resilio Sync/young/Pycharm/Amazon/PhrasalVerbDict/synonym.pd"):
        # 패턴 읽기
        pattern = self.savePattern(patternRoute)
        sameTag = self.saveSameTagPattern(synonymRoute)

        # 패턴 교환
        self.pattern = self.convertPattern(pattern, sameTag)

        # 단어 정제
        self.tokenizer = RegexpTokenizer(r'\w+')
        self.en_stop = get_stop_words('en')
        self.p_stemmer = PorterStemmer()

    # 뽑을 패턴 read
    def savePattern(self, route):
        f = open(route, "r")
        contents = f.readlines()

        pattern = [re.sub("[ \n]", "", i) for i in contents if i != ""]

        return pattern


    # 대신 들어올수 있는 태그 read
    def saveSameTagPattern(self, route):
        sameTag = {}

        f = open(route, "r")
        contents = f.readlines()

        patterns = [i for i in contents if i != ""]

        for i in patterns :
            i = i.replace(" ", "")

            sameTagDiv = i.split("=")
            sameTag[sameTagDiv[0]] = [sameTagDiv[j] for j in range(1, len(sameTagDiv))]

        return sameTag


    def convertPattern(self, pattern, sameTag):
        realPattern = []

        for i in pattern :
            realPattern.append(i)
            for j in str(i).split("+") :
                for k in sameTag :
                    if j == k :
                        for l in sameTag.get(k) :
                            realPattern.append(str(i).replace(j, l))

        return realPattern


    def wordChecking(self, string):
        stopword = ["if", "that"]

        for i in stopword :
            if string.find(i) != -1 :
                return False

        return True


    def wordReplace(self, string):
        list = string.split()

        for i_index, i in enumerate(list) :
            if i == "s" :
                list[i_index] = "is"
            if i == "m" :
                list[i_index] = "am"

        listString = " ".join(list)

        return listString


    # 숙어 처리
    def wordToPhrasalVerb(self, sentence):

        # hypehen 처리
        sentence = sentence.replace("-", "__PYPHEN__")

        # collect token & 불용어 제거
        tokenize = self.tokenizer.tokenize(sentence)
        tagged = [list(i) for i in nltk.pos_tag(tokenize)]

        tag = [i[1] for i in tagged]
        tagString = ";".join(tag)

        for i in self.pattern :
            pvTagString = ";".join(i.split("+"))

            if tagString.find(pvTagString) != -1 :
                pvString = ""

                last = 0 if tagString.find(pvTagString) - 1 < 0 else tagString.find(pvTagString) - 1

                tagString_findRemove = tagString[0:last]

                if tagString_findRemove == "" :
                    tagString_number = 0
                else :
                    tagString_number = tagString_findRemove.count(";") + 1
                pvTagString_number = pvTagString.count(";") + 1

                pvString = " ".join([tagged[j][0] for j in range(tagString_number, tagString_number + pvTagString_number)])

                if not self.wordChecking(pvString) :
                    continue

                pvString = self.wordReplace(pvString)

                sentence = str(sentence).replace(pvString, pvString.replace(" ", "_"))


        # collect token & 불용어 제거
        tokenize = self.tokenizer.tokenize(sentence)
        tagged = [list(i) for i in nltk.pos_tag(tokenize)]

        stopped_tokens = [k for k in tokenize if not k in self.en_stop]


        # pattern 묶기
        for kk_index, kk in enumerate(tagged) :
            if str(kk[0]).find("__PYPHEN__") != -1 :
                tagged[kk_index][0] = tagged[kk_index][0].replace("__PYPHEN__", "-")
                tagged[kk_index][1] = "NN"

            elif str(kk[0]).find("_") != -1 :
                tagged[kk_index][0] = tagged[kk_index][0].replace("_", " ")
                tagged[kk_index][1] = "PV"

        c = 0
        gram_text = ""
        for kk, gram in enumerate(stopped_tokens):
            gram = gram.replace("__PYPHEN__", "-")
            gram = gram.replace("_", " ")
            cc = c

            for jj in range(cc, len(tagged)) :
                if tagged[jj][0] == gram :
                    gram_text += gram + "[" + tagged[jj][1] + "]" + " "
                    c = jj + 1
                    break


            gram_text = gram_text.strip()
            gram_text += "/"

        gram_text = re.sub("/$", "", gram_text)

        return gram_text