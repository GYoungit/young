import os
import re
import MySQLdb
import xlrd
import sys

## pk_id <- 중복일때 에러
## 테이블 있을때 테이블 만들면 에러
## only "\N" == Null
## 가끔씩 int형을 string형으로 인식하는 에러
## 특수문자 처리
## 오류나면 리포팅
## 이름에 뛰어쓰기 있으면 오류나는거 수정


class excelInfo :
    def __init__(self):
        self.workbook = ""
        self.worksheet = ""
        self.nrows = 0
        self.ncolumns = 0
        self.startRows = 0
        self.startColumns = 0
        self.appendHead = True

class DbUtil :
    # name
    base_name = "SQLAlchemy_base"
    model_name = ""

    # account
    user = ""
    password = ""

    # db info
    db_engine = ""
    host = ""
    db_name = ""
    tablename = ""
    charset = ""

    # contents
    base_contents = ""
    model_contents = ""
    class_contents = ""

    # location
    now_location = ""
    start_location = ""

    # data type dictionary
    dataTypeDic = {
        "int" : "Integer",
        "bigint" : "Integer",
        "text" : "Text",
        "longtext" : "Text",
        "mediumtext" : "Text",
        "double" : "Float",
        "float" : "Float",
        "Float" : "Float",
        "varchar" : "String",
        "date" : "Date",
        "datetime" : "Date"
    }
    typeDict = {
        'date' : 'string',
        'varchar(128)' : 'string',
        'varchar(256)' : 'string',
        'varchar(512)' : 'string',
        'text' : 'string',
        'int(11)' : 'number',
        'double' : 'number',

    }

    def __init__(self):
        self.__location_setting("", "")

    def __init__(self, user="root", password="1313"):
        self.__location_setting("", "")
        self.user = user
        self.password = password

    def __init__(self, user="root", password="1313", db_engine="mysql", host="localhost", db_name="", charset="utf8mb4"):
        self.__location_setting("", "")
        self.user = user
        self.password = password
        self.db_engine = db_engine
        self.host = host
        self.db_name = db_name
        self.charset = charset

    # 위치 설정
    def __location_setting(self, now_location, start_location):
        # location setting
        if now_location == "" : now_location = os.getcwd()
        if start_location == "": start_location = "Pycharm"

        self.now_location = now_location
        self.start_location = start_location

        location_list = now_location.split("\\")
        try:
            location_list = location_list[location_list.index(start_location) + 1:]
        except:
            print("\"start_location\" parameter not found...")

        return location_list

    # 해당 db의 column값 불러오기
    def __get_parameter(self):
        db = MySQLdb.connect(self.host, self.user, self.password, self.db_name, charset=self.charset)
        cur = db.cursor(MySQLdb.cursors.DictCursor)
        query = "select * from INFORMATION_SCHEMA.columns where table_schema = \"" + self.db_name + \
                "\" and table_name = \"" + self.tablename + "\""
        cur.execute(query)
        results = cur.fetchall()

        return results

    # db 데이터 타입 가져오기
    def __get_data_type(self, data):
        try:
            time_list = re.split("[\-\/\.]", data)
        except:
            time_list = [None]

        if data == "" :
            return None

        elif type(data) == str:
            data_len = len(data)

            if data_len < 128: return "varchar(128)"
            elif data_len < 256: return "varchar(256)"
            elif data_len < 512: return "varchar(512)"
            else: return "text"

        elif len(time_list) == 3:
            return "date"

        else:
            float_data = str(float(data)).replace(".0", "")
            int_data = str(int(data))

            if float_data == int_data:
                return "int(11)"
            else:
                return "double"

    def __determine_data_type(self, aTybe, bTybe):
        type_level = [None, "date", "int(11)", "double", "varchar(128)", "varchar(256)", "varchar(512)", "text"]
        return aTybe if type_level.index(aTybe) > type_level.index(bTybe) else bTybe

    def __get_excel_parameter(self):
        type_list = []
        data_list = []
        meta_list = []
        c_count = 0

        headNum = 1 if self.excelinfo.appendHead else 0

        for column in range(self.excelinfo.startColumns, self.excelinfo.ncolumns):
            type_list.append(None)
            meta_list.append(str(self.excelinfo.worksheet.cell_value(self.excelinfo.startRows, column)).strip().replace(" ", "_"))

        for row in range(self.excelinfo.startRows + headNum, self.excelinfo.nrows) :
            row_data_list = []
            for column in range(self.excelinfo.startColumns, self.excelinfo.ncolumns) :
                data = self.excelinfo.worksheet.cell_value(row, column)
                type_list[c_count] = self.__determine_data_type(type_list[c_count], self.__get_data_type(data))
                row_data_list.append(data)

                c_count += 1
            data_list.append(row_data_list)
            c_count = 0

        return type_list, meta_list, data_list

    def __parameterToText(self, params):
        parameter_String = ""

        for param in params :
            column_name = param.get("COLUMN_NAME")
            column_key = param.get("COLUMN_KEY")
            column_type = param.get("COLUMN_TYPE")
            ordinal_position = param.get("ORDINAL_POSITION")
            is_nullable = param.get("IS_NULLABLE")

            try:
                cLength = re.sub("[\(\)]", "", re.findall("\(.*\)", column_type)[0])
            except IndexError:
                pass
            cType = re.sub("\(.*\)", "", column_type)

            parameter_String += column_name + " = Column("

            if self.dataTypeDic.get(cType) == "String" :
                parameter_String += self.dataTypeDic.get(cType) + "(" + cLength + ")"
            else : parameter_String += self.dataTypeDic.get(cType)

            if column_key == "PRI" :
                parameter_String += ",primary_key=True"
            else : pass

            parameter_String += ")\n\t"

        return parameter_String + "\n"

    def __make_model_constructor(self, params):
        constructorString = ""
        printString = ""

        constructorString += "\tdef __init__(self, "

        for param in params :
            column_name = param.get("COLUMN_NAME")
            column_key = param.get("COLUMN_KEY")
            if column_key == "PRI" : continue

            constructorString += column_name + ", "

        constructorString = re.sub(", $", "", constructorString) + ") :\n\t\t"

        for param in params :
            column_name = param.get("COLUMN_NAME")
            column_key = param.get("COLUMN_KEY")
            if column_key == "PRI" : continue

            constructorString += "self." + column_name + " = " + column_name + "\n\t\t"
            printString += column_name + ", "

        printString = re.sub(", $", "", printString)
        print(printString)

        return constructorString

    def __make_model_repr(self, params, tableName):
        reprString = "\n"

        reprString += '\tdef __repr__(self) :\n\t\t'
        reprString += 'return \"<' + tableName + '('

        for i in range(len(params)) :
            reprString += "\'%s\',"

        reprString = re.sub(",$", "", reprString)
        reprString += ">\" % ("

        for param in params :
            column_name = param.get("COLUMN_NAME")
            reprString += "self." + column_name + ", "

        reprString = re.sub(", $", "", reprString) + ")"

        return reprString

    def __model_add_importer(self, now_location, start_location):
        location_list = self.__location_setting(now_location, start_location)
        location_list.append(self.base_name)

        base_import_content = ".".join(location_list)

        self.model_contents = "from sqlalchemy import Column, Integer, String, Date, Text, Float" + "\n"
        self.model_contents += "from sqlalchemy import ForeignKey" + "\n"
        self.model_contents += "from sqlalchemy.orm import relationship, backref" + "\n"

        self.model_contents += "from " + base_import_content + " import Base" + "\n\n"

    def __model_add_class(self, table_name, param):
        # 추가예정
        pass

    # 추가 예정
    def __model_many_to_many(self):
        # 추가예정
        pass

    # 추가 예정
    def __model_many_to_one(self):
        # 추가예정
        pass

    # 추가 예정
    def __model_one_to_many(self):
        # 추가예정
        pass

    # 추가 예정
    def __model_one_to_one(self):
        # 추가예정
        pass

    def __get_excel_start_numbering(self, file_location, sheetName):
        excelinfo = excelInfo()

        excelinfo.startRows = -1
        excelinfo.startColumns = -1
        excelinfo.workbook = xlrd.open_workbook(file_location)

        if sheetName != None :
            excelinfo.worksheet = excelinfo.workbook.sheet_by_name(sheetName)
        else :
            excelinfo.worksheet = excelinfo.workbook.sheet_by_index(0)

        excelinfo.nrows = excelinfo.worksheet.nrows
        excelinfo.ncolumns = excelinfo.worksheet.ncols

        for i in range(100) :
            x_axis_data = excelinfo.worksheet.cell_value(i, excelinfo.ncolumns - 1)
            y_axis_data = excelinfo.worksheet.cell_value(excelinfo.nrows - 1, i)

            if y_axis_data != "" and excelinfo.startColumns == -1 :
                excelinfo.startColumns = i
            if x_axis_data != "" and excelinfo.startRows == -1 :
                excelinfo.startRows = i

            if excelinfo.startColumns != -1 and excelinfo.startRows != -1 :
                break

        if excelinfo.startColumns == -1 or excelinfo.startRows == -1 :
            raise ExcelDataNotReadError

        return excelinfo

    def __type_Converter(self, data, type):
        if str(type).find("varchar") != -1 or str(type) == "date" or str(type) == "text" :
            returnData = "'" + str(data) + "'"

        elif str(type).find("int") != -1 :
            try:
                returnData = str(int(data))
            except:
                returnData = "null"

        elif str(type) == "float" or str(type) == "double" :
            try:
                returnData = str(float(data))
            except:
                returnData = "null"

        return returnData

    def __make_db_table_and_insert_data(self, make_table_name):
        # get excel param
        typeData, metaData, contentsData = self.__get_excel_parameter()

        # mysql
        print("create table...")
        db = MySQLdb.connect(host=self.host, user=self.user, password=self.password, db=self.db_name, charset=self.charset)
        cur = db.cursor(MySQLdb.cursors.DictCursor)
        ########### id가 있을경우 처리해야됨
        # create table
        selectQuery = "CREATE TABLE " + make_table_name + "(\n" \
                      + "pk_id int(11) unsigned NOT NULL AUTO_INCREMENT,\n"
        charsetQuery = "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"

        for i in range(len(metaData)) :
            if metaData[i].lower() == "pk_id" :
                continue

            if typeData[i] == None :
                typeData[i] = "varchar(128)"

            selectQuery += metaData[i] + " " + typeData[i]
            if self.typeDict.get(typeData[i]) == 'string' : selectQuery += " " + charsetQuery
            selectQuery += ",\n"

        selectQuery += "PRIMARY KEY (pk_id)\n);"

        cur.execute(selectQuery)

        # insert data
        print("insert into data...")

        for i in range(len(contentsData)) :
            print(str(i) + " / " + str(len(contentsData)))
            selectQuery = "Insert into " + make_table_name + "\n"
            selectQuery += "VALUES\n"

            selectQuery += "(" + str(i + 1) + ","
            for j in range(len(contentsData[i])) :
                input_contents_data = contentsData[i][j]
                if self.typeDict.get(typeData[j]) == "string" :
                    input_contents_data = str(input_contents_data).replace("\'", "\\\'").replace(",", "")
                selectQuery += self.__type_Converter(input_contents_data, typeData[j]) + ","

            selectQuery = re.sub(",$", "", selectQuery)
            selectQuery += "),\n"

            selectQuery = re.sub(",\n$", ";", selectQuery)
            cur.execute(selectQuery)

            db.commit()

    def set_login_info(self, user, password):
        self.user = user
        self.password = password

    def set_file_location(self, now_location="", start_location=""):
        self.__location_setting(now_location, start_location)

    def set_db_info(self, db_engine="mysql", host="localhost", db_name="", table_name=None, charset="utf8mb4"):
        self.db_engine = db_engine
        self.host = host
        self.db_name = db_name
        self.tablename = table_name
        self.charset = charset

    def make_SQLAlchemy_base(self, file_name="SQLAlchemy_base", convert_unicode=False, echo=True, now_location="", start_location="") :
        self.base_name = file_name
        db_info = self.db_engine + "://" + self.user + ":" + self.password + "@" + self.host + "/" + self.db_name + "?" + "charset=" + self.charset

        self.base_contents = "from sqlalchemy import create_engine" + "\n"
        self.base_contents += "from sqlalchemy.ext.declarative import declarative_base" + "\n"
        self.base_contents += "from sqlalchemy.orm import scoped_session, sessionmaker" + "\n\n"

        self.base_contents += "engine = create_engine(\"" + db_info + "\"" + ", convert_unicode=" + str(convert_unicode) + ", echo=" + str(echo) + ")\n"
        self.base_contents += "db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))" + "\n\n"

        self.base_contents += "Base = declarative_base()" + "\n"
        self.base_contents += "Base.query = db_session.query_property()" + "\n\n"

        self.base_contents += "def init_db() :" + "\n\t"
        self.base_contents += "Base.metadata.create_all(engine)"

        with open(self.now_location + "\\" + file_name + ".py", 'w') as f :
            f.write(self.base_contents)

        print("db_session.add(t)\ndb_session.commit()")

    def make_db_model(self, model_name=None, now_location="", start_location="") :
        sys_stack = []

        # beginning setting
        if model_name == None : model_name = self.tablename + "_model"
        if self.tablename == None : raise TableNotFoundError

        # add import
        self.__model_add_importer(self.now_location, self.start_location)

        self.model_contents += "class " + model_name + "(Base):" + "\n\t"
        self.model_contents += "__tablename__ = '" + self.tablename + "'" + "\n\n\t"

        # call stack check
        for depth in range(100) :
            try:
                function_name = sys._getframe(depth).f_code.co_name
                py_name = re.split("[\\\\/]", sys._getframe(depth).f_code.co_filename)[-1]
            except:
                break

            if py_name == "DbUtil.py" and function_name != "<module>" :
                sys_stack.append(function_name)

        sys_stack.reverse()

        # param/constructor setting
        if sys_stack[0] == "make_db_model" :
            param = self.__get_parameter()

        elif sys_stack[0] == "excelToDB" :
            param = self.__get_excel_parameter()

        paramString = self.__parameterToText(param)
        constructorString = self.__make_model_constructor(param)
        reprString = self.__make_model_repr(param, self.tablename)

        self.model_contents += paramString
        self.model_contents += constructorString
        self.model_contents += reprString

        with open(self.now_location + "\\" + model_name + ".py", 'w') as f :
            f.write(self.model_contents)

    def excelToDB(self, make_table_name, file_location, sheetName=None, appendHead=True):
        print("excel collecting info...")
        excelinfo = self.__get_excel_start_numbering(file_location, sheetName)
        excelinfo.appendHead = appendHead

        # 전역으로 넘기기
        self.excelinfo = excelinfo
        # table 생성과 데이터 넣기
        self.__make_db_table_and_insert_data(make_table_name)


class TableNotFoundError(Exception) :
    def __str__(self):
        return "Table Not Found"
class ExcelDataNotReadError(Exception) :
    def __str__(self):
        return "Excel Data Not Read"

if __name__ == '__main__':
    # # argv
    # user_name = sys.argv[1]
    # password = sys.argv[2]
    # host = sys.argv[3]
    # db_name = sys.argv[4]
    # create_tableName = sys.argv[5]
    # excel_location = sys.argv[6]
    #
    # # db util
    # dbutil = DbUtil()
    # dbutil.set_db_info(db_name=db_name, host=host)
    # dbutil.set_login_info(user=user_name, password=password)
    #
    # dbutil.excelToDB(create_tableName, excel_location)


    # db util
    dbutil = DbUtil()
    dbutil.set_db_info(db_name="2017_point_business", host="203.230.103.21")
    dbutil.set_login_info(user="ckAdmin", password="iip12345")

    dbutil.excelToDB("subject_week_info_test", "D:/강의계획서 2번.xlsx")