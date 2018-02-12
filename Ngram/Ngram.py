# 1. parser를 돌린 후 한 단어를 기준으로 중심에서 그 단어와 주변 단어 비교
# 2. parser를 돌린 후 모든 단어 기준에서 모든 단어와 비교

# parsing 된 단어(LSU)와 parsing 된 모든 단어(tag)의 순번 모두 가중치로 사용

## c_word또한 합성어 처리 해줘야 함 ex)약한 = 약하 + -ㄴ

## db변경 필요 (word_info의 pk를 숫자로 / 같은 단어이면서 다른 품사 문제생김)
## 모든 단어에 대해 reverse 태그 달기

import re
import copy
import configparser
from sqlalchemy import or_, and_

from pyModule.DB.DbUtil import DbUtil
from pyModule.RealParser.realParserAPI import RealParser
from pyModule.logging.log_module import Log
from pyModule.Ngram.dbmodel.SQLAlchemy_base import db_session
from pyModule.Ngram.dbmodel.db_model import learning_sentence_model, word_class_relation_model, word_relation_simlarity_model, word_info_model

class CWordNotMatchingError(Exception):
    def __str__(self):
        return "c_word and sentence not matching..."

class WordTable:
    def __init__(self, word, contain, tag, index, ec):
        self.word = word
        self.contain = contain
        self.tag = tag
        self.index = index
        self.ec = ec

class WordListingTable:
    def __init__(self, wordA, wordB, length):
        self.wordA = wordA
        self.wordB = wordB
        self.length = length

class Ngram:
    # tag parameter
    dot_tag = "SF"
    space_tag = "SX"
    enter_tag = ""
    context_tag = "EC"

    analysis_tag = ['SL', 'NNG', 'NNP', 'NNPC', 'NNV', 'NNGV', 'NNGA', 'VV', 'VA', 'EC']
    get_similarity_tag = ['SL', 'NNG', 'NNP', 'NNPC', 'NNV', 'NNGV', 'NNGA', 'VV', 'VA']
    need_tag = ['SL', 'NNG', 'NNP', 'NNPC', 'NNV', 'NNGV', 'NNGA', 'VV', 'VA', 'MAG', 'XR']
    extract_tag = ['SL', 'NNG', 'NNP', 'NNPC', 'NNV', 'NNGV', 'NNGA', 'VV', 'VA', 'MAG', 'XR', 'VX']

    word_class_dict = {'NNGV' : '동사',
                       'NNV' : '동사',
                       'VV' : '동사',

                       'SL' : '명사',
                       'NNG' : '명사',
                       'NNPC' : '명사',
                       'NNP' : '명사',

                       'NNGA' : '형용사',
                       'VA' : '형용사'}


    def __init__(self, dbconf=None):
        # korean parser
        self.parser = RealParser()

        # log
        self.log = Log()

        if dbconf != None :
            # db setting read
            config = configparser.ConfigParser()
            config.read(dbconf)

            dbutil = DbUtil()
            dbutil.set_db_info(host=config.get("db_info", 'host'),
                               db_name=config.get("db_info", 'db_name'),
                               table_name=config.get("db_info", 'table_name'),
                               charset=config.get("db_info", 'charset'))

            dbutil.set_login_info(user=config.get("user_info", 'user_id'),
                                  password=config.get("user_info", 'password'))

            dbutil.make_SQLAlchemy_base()

    # c_word가 sentence에 존제하는지 확인
    def __same_search(self, parsingWord):
        c_word = self.parsingCWord
        for wordList in parsingWord :
            for word in wordList :
                if (word.get('surface').find("##") != -1 and word.get('tag') != "SY") or \
                        (word.get('surface') == c_word.get('surface') and word.get('tag') == c_word.get('tag')):
                    return False

        return True

    # parsing된 단어 정제
    def __refinement_parsing_word(self, parsingWord, need_tag, isCWord):
        remove_number_list = []

        if isCWord :
            for i_index, i in enumerate(parsingWord) :
                try:
                    if need_tag.index(i.get('tag')) >= 0 :
                        continue
                except:
                    if i.get('c_word') : continue
                    remove_number_list.append(i_index)

            remove_number_list.reverse()

            for i in remove_number_list :
                del parsingWord[i]

        else :
            for i_index, i in enumerate(parsingWord):
                remove_number_list = []
                for j_index, j in enumerate(i):
                    try:
                        if need_tag.index(j.get('tag')) >= 0:
                            continue
                    except:
                        if j.get('c_word'): continue
                        remove_number_list.append(j_index)

                remove_number_list.reverse()

                for j in remove_number_list:
                    del parsingWord[i_index][j]

        if isCWord : parsingWord = self.__merge_tag(parsingWord)
        else :
            parsingWord = [i for i in parsingWord if i != []]

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

        # 부정 찾기
        try:
            for i in range(save_index[-1] + 1, save_index[-1] + 1 + 5) :
                for word in parsingWord[i] :
                    if word.get('surface') == "않" and word.get('tag') == "VX" :
                        c_word['reverse'] = True
        except:
            pass

        if check :
            for i in range(save_index[0], save_index[-1] + 1) :
                del parsingWord[save_index[0]]

            parsingWord.insert(save_index[0], [c_word])

        return parsingWord

    # class를 EC태그로 나누기
    def __split_tag_using_class(self, sentence):
        results = []
        in_list = []

        for word in sentence :
            if word.ec :
                if in_list == []: continue
                results.append(in_list)
                in_list = []
                continue
            in_list.append(word)

        if in_list != []: results.append(in_list)

        return results

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

                            results.append([[input_json]])

                            check = True
            if check :
                check = not check
                continue
            results.append(sentence)

        return results

    # 가중치 관련 db작업
    def __similarity_db_work(self, wordList):
        listing = []
        listing_original = []
        for i_index, i in enumerate(wordList):
            for j_index, j in enumerate(wordList):
                if i_index >= j_index : continue
                list_for_sorting = sorted([i, j], key=lambda ww: ww.word)

                listing.append(WordListingTable(list_for_sorting[0], list_for_sorting[1], abs(list_for_sorting[0].index - list_for_sorting[1].index)))
                listing_original.append(WordListingTable(i, j, abs(i.index - j.index)))

        for i_index, i in enumerate(listing):
            wiA_model = None
            wiB_model = None
            there_is_word_A = False
            there_is_word_B = False

            if len(i.wordA.word) > 50 or len(i.wordB.word) > 50 or i.wordA.word.lower() == i.wordB.word.lower() :
                continue

            ### word_info
            # word_info에 등록되어있는지 확인
            there_is_word_A = True if db_session.query(word_info_model.word).filter(word_info_model.word == i.wordA.word).first() != None else False
            there_is_word_B = True if db_session.query(word_info_model.word).filter(word_info_model.word == i.wordB.word).first() != None else False

            # word_info에 등록되어있지 않으면 모델 생성
            if not there_is_word_A : wiA_model = word_info_model(i.wordA.word, i.wordA.tag, self.word_class_dict.get(i.wordA.tag), str(i.wordA.contain))
            if not there_is_word_B : wiB_model = word_info_model(i.wordB.word, i.wordB.tag, self.word_class_dict.get(i.wordB.tag), str(i.wordB.contain))

            # word_info 모델이 None이 아니라면 세션에 추가
            if wiA_model != None: db_session.add(wiA_model)
            if wiB_model != None: db_session.add(wiB_model)

            # word_info먼저 commit / FK
            db_session.commit()


            ### word_relation_simlarity
            wr_check_query = db_session.query(word_relation_simlarity_model)\
                .filter(or_(word_relation_simlarity_model.word1 == i.wordA.word, word_relation_simlarity_model.word2 == i.wordB.word))

            if wr_check_query.first() == None :
                try:
                    length = 1.0/i.length
                except:
                    length = 1.0
                wrs_model = word_relation_simlarity_model(i.wordA.word, i.wordB.word, 1, i.length, length)
                db_session.add(wrs_model)
            else :
                wr = wr_check_query.first()
                wr.relation_count += 1
                wr.distance_sum += i.length
                try:
                    wr.similarity = float(wr.relation_count / float(wr.distance_sum))
                except:
                    wr.similarity = 1

            ### word_class_relation
            o_i = listing_original[i_index]
            if (self.word_class_dict.get(o_i.wordA.tag) == "명사" and self.word_class_dict.get(o_i.wordB.tag) == "동사") or \
                    (self.word_class_dict.get(o_i.wordA.tag) == "형용사" and self.word_class_dict.get(o_i.wordB.tag) == "명사") or \
                    (self.word_class_dict.get(o_i.wordA.tag) == "형용사" and self.word_class_dict.get(o_i.wordB.tag) == "동사") :
                wc_check_query = db_session.query(word_class_relation_model)\
                    .filter(or_(word_class_relation_model.word1 == o_i.wordA.word, word_class_relation_model.word2 == o_i.wordB.word))

                if wc_check_query.first() == None :
                    wc_model = word_class_relation_model(o_i.wordA.word, o_i.wordB.word, 1)
                    db_session.add(wc_model)
                else :
                    wc = wc_check_query.first()
                    wc.relation_count += 1

        db_session.commit()

    # 가중치 계산
    def __similarity_calculation(self, contextSentenceList):
        word_table_list = []

        for cs_index, contextSentence in enumerate(contextSentenceList):
            for sentence in contextSentence :
                for word in sentence :
                    word_table_list.append(WordTable(word.get('surface'), word.get('contain'), word.get('tag'), cs_index, True if word.get('tag') == "EC" else False))

        # c_word가 합쳐져있다면 나누기
        ec_tag_split = self.__split_tag_using_class(word_table_list)

        for unit in ec_tag_split :
            self.__similarity_db_work(unit)

    # 가중치 불러오기
    def __get_similarity(self, contextSentenceList, results_print):
        word_list = []
        # 가중치를 불러올 단어 정제
        for contextSentence in contextSentenceList :
            for word in contextSentence :
                for i in word :
                    if i.get("tag") == "EC": continue
                    word_list.append(i)

        if results_print :
            wr_dict = {}

            ## 가중치 불러오기
            for i_index, i in enumerate(word_list) :
                for j_index, j in enumerate(word_list) :
                    if i_index >= j_index : continue
                    similarity = 0.0
                    list_for_sorting = sorted([i, j], key=lambda ww: ww.get("surface"))
                    ck_query = db_session.query(word_relation_simlarity_model)\
                        .filter(and_(word_relation_simlarity_model.word1==list_for_sorting[0].get("surface"),
                                    word_relation_simlarity_model.word2==list_for_sorting[1].get("surface")))
                    sim_query = ck_query.first()
                    if sim_query == None :
                        continue
                    else:
                        similarity = sim_query.similarity

                    wr_dict.setdefault(i.get('surface'), {})
                    in_dict = wr_dict.get(i.get('surface'))
                    in_dict.setdefault(j.get('surface'), similarity)

            # 단방향 -> 양방향
            r_wr_dict = copy.deepcopy(wr_dict)
            for i in wr_dict :
                for j in wr_dict.get(i) :
                    r_wr_dict.setdefault(j, {})
                    in_dict = r_wr_dict.get(j)
                    in_dict.setdefault(i, wr_dict.get(i).get(j))

            return r_wr_dict

    # 문단을 원하는 tag로 끊기
    def __split_tag_using_dict(self, paragraph, tag):
            sentenceList = [[]]
            removeNumList = []
            sListIndex = 0

            for p_index, i in enumerate(paragraph):
                if type(i) == list: i = i[0]
                if i.get('tag') == tag:
                    sListIndex += 1
                    sentenceList.append([])
                    continue

                sentenceList[sListIndex].append(paragraph[p_index])

            # 공백 제거
            for i_index, i in enumerate(sentenceList):
                if i == []: removeNumList.append(i_index)

            removeNumList.reverse()
            for i in removeNumList: del sentenceList[i]

            return sentenceList

    # 문장과 c_word 설정
    def set_sentence_and_cword(self, sentence, c_word=None):
        self.sentence = sentence
        self.c_word = c_word

        # sentence parsing 하기 & 정제하기
        try:
            self.parsingTaggingWord = self.__make_original_word(self.parser.getParsingTag(self.sentence).get('result_list'))
        except:
            return False

        if c_word != None:
            # c_word parsing 하기 & 정제하기
            self.parsingCWord = self.__refinement_parsing_word(
                self.parser.getParsingTag(self.c_word).get('result_list'), self.extract_tag, True)

            self.parsingTaggingWord = self.__c_word_check_and_sum_word(self.parsingTaggingWord)
            self.parsingWord = self.__refinement_parsing_word(copy.deepcopy(self.parsingTaggingWord), self.need_tag, False)

            if self.__same_search(self.parsingTaggingWord):
                self.c_word_search = False
                return False
                # raise CWordNotMatchingError
        self.c_word_search = True
        return True

    # c_word 주변단어 뽑기
    def get_surround_word(self, surroundNumber=2, front=True, rear=False):
        c_word_index = -1
        results_dict = {}
        check = False

        if not self.c_word_search :
            return False

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

    # 단어 가중치 뽑기
    def get_word_weight(self, results_print=True):
        contextSentenceList = []

        # 문장단위로 나누기
        sentenceList = self.__split_tag_using_dict(self.parsingTaggingWord, self.enter_tag)

        # sentence db에 저장
        ls_model = learning_sentence_model(self.sentence)
        db_session.add(ls_model)

        for sentence in sentenceList:
            contextSentenceList = self.__split_tag_using_dict(sentence, self.space_tag)

            # 문맥단위로 나누기
            for contextSentence in contextSentenceList:
                self.__refinement_parsing_word(contextSentence, self.analysis_tag, False)

            if self.c_word != None: contextSentenceList = self.__split_sentence_tag(contextSentenceList)

            # 가중치 계산
            self.__similarity_calculation(contextSentenceList)

        # 가중치 가져오기
        sim = self.__get_similarity(contextSentenceList, results_print)


if __name__ == '__main__':
    na = Ngram()
    na.set_sentence_and_cword("힘이 약한 철수는 단순 이동수단을 가지고 있어 편하게 짐을 옮겼다.", c_word="옮기다")
    na.get_surround_word(surroundNumber=3, rear=True)
    srWeight = na.get_word_weight()
