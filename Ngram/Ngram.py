# 1. parser를 돌린 후 한 단어를 기준으로 중심에서 그 단어와 주변 단어 비교
# 2. parser를 돌린 후 모든 단어 기준에서 모든 단어와 비교

# parsing 된 단어(LSU)와 parsing 된 모든 단어(tag)의 순번 모두 가중치로 사용

## c_word또한 합성어 처리 해줘야 함 ex)약한 = 약하 + -ㄴ

import MySQLdb
import ngram
import json
import re
import copy

from pyModule.RealParser.realParserAPI import RealParser
from pyModule.logging.log_module import Log

class CWordNotMatchingError(Exception):
    def __str__(self):
        return "c_word and sentence not matching..."

class Ngram:

    # tag parameter
    dot_tag = "SF"
    space_tag = "SX"
    enter_tag = ""

    analysis_tag = ['SL', 'NNG', 'NNP', 'NNPC', 'NNV', 'NNGV', 'NNGA', 'VV', 'VA', 'EC']
    need_tag = ['SL', 'NNG', 'NNP', 'NNPC', 'NNV', 'NNGV', 'NNGA', 'VV', 'VA', 'MAG', 'XR']
    extract_tag = ['SL', 'NNG', 'NNP', 'NNPC', 'NNV', 'NNGV', 'NNGA', 'VV', 'VA', 'MAG', 'XR', 'VX']

    verb = ['NNGV', 'NNV', 'VV']
    adjective = ['NNGA', 'VA']
    noun = ['SL', 'NNG', 'NNPC', 'NNP']

    def __init__(self):
        # korean parser
        self.parser = RealParser()

        # log
        self.log = Log()

        # mysql
        db = MySQLdb.connect(host="localhost", user="root", password="1313", db="amazon", charset="utf8")
        cur = db.cursor(MySQLdb.cursors.DictCursor)

    # c_word가 sentence에 존제하는지 확인
    def __same_search(self, parsingWord):
        for wordList in parsingWord :
            for word in wordList :
                if word.get('surface').find("##") != -1 and word.get('tag') != "SY":
                    return False

        return True

    # parsing된 단어 정제
    def __refinement_parsing_word(self, parsingWord, need_tag, isCWord):
        remove_number_list = []

        # 필요없는 tag를 가진 word 제거
        for i_index, i in enumerate(parsingWord) :
            if type(i) == list: i = i[0]

            try:
                if need_tag.index(i.get('tag')) >= 0 :
                    continue
            except:
                if i.get('c_word') : continue
                remove_number_list.append(i_index)

        remove_number_list.reverse()

        for i in remove_number_list :
            del parsingWord[i]

        if isCWord : parsingWord = self.__merge_tag(parsingWord)

        return parsingWord

    # c_word에 해당하는 여러 태그 하나로 합치기
    def __merge_tag(self, parsingWord):
        returnData = {}

        # 남은거 합치기
        for i in parsingWord :
            returnData.setdefault('surface', '')
            returnData.setdefault('tag', '')
            returnData.setdefault('idx', '')
            returnData.setdefault('exp', '')
            returnData.setdefault('c_word', True)
            returnData.setdefault('reverse', False)

            returnData['surface'] += i.get('surface') + "##"
            returnData['tag'] += i.get('tag') + "##"
            returnData['idx'] += str(i.get('idx')) + "##"
            returnData['exp'] += str(i.get('exp')) + "##"

        returnData['surface'] = re.sub("##$", "", returnData['surface'])
        returnData['tag'] = re.sub("##$", "", returnData['tag'])
        returnData['idx'] = re.sub("##$", "", returnData['idx'])
        returnData['exp'] = re.sub("##$", "", returnData['exp'])

        return returnData

    # 원형으로 만들기
    def __make_original_word(self, parsingWord):
        results = []

        for word in parsingWord :
            in_results = []
            if word.get('tag').find("+") != -1 :
                for index in range(word.get('tag').count("+") + 1):
                    input_json = {}
                    input_json['surface'] = word.get('exp').split("+")[index].split("/")[0]
                    input_json['tag'] = word.get('tag').split("+")[index]
                    input_json['idx'] = word.get('idx')
                    input_json['exp'] = word.get('exp').split("+")[index]

                    in_results.append(input_json)

            if in_results == []: results.append([word])
            else : results.append(in_results)

        return results

    # 2음절 이상인 문장 합치기
    def __c_word_check_and_sum_word(self, parsingWord):
        connecting_word_tag = ['JKS', 'JX', 'JKO', 'MAG', 'SX']
        save_index = []
        check = False
        count = 0

        c_word = self.parsingCWord
        base_tag_list = c_word.get('tag').split('##')
        base_surface_list = c_word.get('surface').split('##')
        max_count = len(base_tag_list)

        for word_index, word_list in enumerate(parsingWord) :
            now = False

            for index in range(len(base_tag_list)) :
                for word in word_list :
                    if word.get('tag') == base_tag_list[index] and word.get('surface') == base_surface_list[index] :
                        save_index.append(word_index)
                        check = True
                        now = True
                        count += 1
                        break

            if max_count == count :
                break

            try:
                if now or connecting_word_tag.index(word.get('tag')) > -1 :
                    continue
            except ValueError:
                if check:
                    check = False
                    break
                else:
                    continue

        for i in range(save_index[-1] + 1, save_index[-1] + 1 + 5) :
            for word in parsingWord[i] :
                if word.get('surface') == "않" and word.get('tag') == "VX" :
                    c_word['reverse'] = True

        if check :
            for i in range(save_index[0], save_index[-1] + 1) :
                del parsingWord[save_index[0]]

            parsingWord.insert(save_index[0], [c_word])

        return parsingWord

    # 문장과 c_word 설정
    def set_sentence_and_cword(self, sentence, c_word=None):
        self.sentence = sentence
        self.c_word = c_word

        # sentence parsing 하기 & 정제하기
        self.parsingTaggingWord = self.__make_original_word(self.parser.getParsingTag(self.sentence).get('result_list'))

        if c_word != None:
            # c_word parsing 하기 & 정제하기
            self.parsingCWord = self.__refinement_parsing_word(
                self.parser.getParsingTag(self.c_word).get('result_list'), self.extract_tag, True)

            self.parsingTaggingWord = self.__c_word_check_and_sum_word(self.parsingTaggingWord)
            self.parsingWord = self.__refinement_parsing_word(copy.copy(self.parsingTaggingWord), self.need_tag, False)

            if self.__same_search(self.parsingTaggingWord):
                return False
                # raise CWordNotMatchingError
        return True

    # c_word 주변단어 뽑기
    def get_surround_word(self, surroundNumber=2, front=True, rear=False):
        c_word_index = -1
        results_dict = {}
        check = False

        c_word_surface = self.parsingCWord.get('surface')

        parsingTaggingWord = self.parsingTaggingWord
        parsingWord = self.parsingWord

        for tw_index, tagWord in enumerate(parsingTaggingWord) :
            if check : break
            for word in tagWord :
                if word.get('c_word'):
                    c_word_index = tw_index
                    check = True
                    break

        parsingWordSurface = [i[0].get('surface') for i in parsingWord]

        if front : # 앞
            ftf = c_word_index + 1
            ftr = c_word_index + 1 + surroundNumber if c_word_index + 1 + surroundNumber < len(parsingTaggingWord) else len(parsingTaggingWord)
            ff = parsingWordSurface.index(c_word_surface) + 1
            fr = parsingWordSurface.index(c_word_surface) + 1 + surroundNumber if parsingWordSurface.index(c_word_surface) + 1 + surroundNumber < len(parsingTaggingWord) else len(parsingTaggingWord)

            results_dict["fTagWord"] = parsingTaggingWord[ftf:ftr]
            results_dict["fWord"] = parsingWord[ff:fr]

        if rear : # 뒤
            rtf = c_word_index - surroundNumber if c_word_index - surroundNumber >= 0 else 0
            rtr = c_word_index
            rf = parsingWordSurface.index(c_word_surface) - surroundNumber if parsingWordSurface.index(c_word_surface) - surroundNumber > 0 else 0
            rr = parsingWordSurface.index(c_word_surface)

            results_dict["rTagWord"] = parsingTaggingWord[rtf:rtr]
            results_dict["rWord"] = parsingWord[rf:rr]


        return results_dict

    # 문단을 원하는 tag로 끊기
    def __split_tag(self, paragraph, tag):
        sentenceList = [[]]
        removeNumList = []
        sListIndex = 0

        for p_index, i in enumerate(paragraph) :
            if type(i) == list : i = i[0]
            if i.get('tag') == tag :
                sListIndex += 1
                sentenceList.append([])
                continue

            sentenceList[sListIndex].append(paragraph[p_index])

        # 공백 제거
        for i_index, i in enumerate(sentenceList) :
            if i == []: removeNumList.append(i_index)

        removeNumList.reverse()
        for i in removeNumList: del sentenceList[i]

        return sentenceList

    # ##으로 묶은 태그 나누기
    def __split_sentence_tag(self, sentenceList):
        results = []
        check = False

        for sentence in sentenceList:
            for word_list in sentence :
                for word in word_list :
                    if word.get("surface").find("##") != -1 and word.get("tag").find("##") != -1 :
                        for index in range(word.get("tag").count("##") + 1) :
                            input_json = {}
                            input_json['surface'] = word.get("surface").split("##")[index]
                            input_json['tag'] = word.get("tag").split("##")[index]
                            input_json['idx'] = word.get("idx").split("##")[index]
                            input_json['exp'] = word.get("exp").split("##")[index]
                            input_json['c_word'] = word.get("c_word")
                            input_json['reverse'] = word.get("reverse")

                            results.append([input_json])

                            check = True
            if check :
                check = not check
                continue
            results.append(sentence)

        return results

    def __similarity_calculation(self, contextSentenceList):
        return None

    # 단어 가중치 뽑기
    def get_word_weight(self):
        contextSentenceList = []
        csListIndex = 0

        sentenceList = self.__split_tag(self.parsingTaggingWord, self.enter_tag)

        for sentence in sentenceList:
            contextSentenceList = self.__split_tag(sentence, self.space_tag)

            for contextSentence in contextSentenceList:
                self.__refinement_parsing_word(contextSentence, self.analysis_tag, False)

            if self.c_word != None: contextSentenceList = self.__split_sentence_tag(contextSentenceList)

            sim = self.__similarity_calculation(contextSentenceList)



if __name__ == '__main__':
    na = Ngram()
    na.set_sentence_and_cword("힘이 약한 철수는 단순 이동수단을 가지고 있어. 편하게 짐을 옮긴다.", "힘이 약하다")
    srDict = na.get_surround_word(surroundNumber=50, front=True, rear=True)
    srWeight = na.get_word_weight()