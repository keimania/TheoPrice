""" 청산결제 오라클서버에 접근  
  Date:
    2023-11-10
  Author:
    구자민
"""

import oracledb
import os

class RDB_client:

    def make_connection(self, env_name:str):
        """환경명을 기입하면 해당 오라클DB에 접속
        """

        # 오라클 인스턴트 클라이언트 설치 경로
        INSTANT_LOCATION = r"D:\app\client\NO160\product\19.0.0\client_1\instantclient"
        # 출력파일의 상위 경로
        DIRECTORY_LOCATION = r".\NextGen\output"
        # 환경변수 등록
        os.environ["PATH"] = INSTANT_LOCATION + ";" + os.environ["PATH"]

        # 오라클 접속 정보
        env_info = {            
            'PD_CS_CCP' : {'name' : '가동 장내청산','id': "USCS_CCP",'passwd': "", 'hostname': ""},
            'PD_CS_OTC' : {'name' : '가동 장외청산','id': "USCS_OTC",'passwd': "", 'hostname': ""},
            'PD_RK_CCP' : {'name' : '가동 장내리스크','id': "USRK_CCP",'passwd': "", 'hostname': ""},
            'PD_RK_OTC' : {'name' : '가동 장외리스크','id': "USRK_OTC",'passwd': "", 'hostname': ""}
        }
        self.name = env_info[env_name]['name']
        self.user_name = env_info[env_name]['id']
        self.password = env_info[env_name]['passwd']
        self.host_info = env_info[env_name]['hostname']
        
        self.connection = oracledb.connect(user=self.user_name, password=self.password, dsn=self.host_info)
        self.cursor = self.connection.cursor()

        return self


    def execute_sql(self, sql: str):
        """SQL 실행
        """
        self.cursor.execute(sql)

    def get_column_names(self):
        """컬럼명 가져오기
        """
        return [col[0] for col in self.cursor.description]

    def get_datas(self):
        """전체 데이터 가져오기
        """
        return self.cursor.fetchall()
    
    def get_data(self):
        """전체 데이터 중 첫줄만 가져오기
        """
        return self.cursor.fetchone()                  
    
    def get_name(self):
        """데이터베이스의 user id 가져오기
        """
        return self.name

    def get_username(self):
        """데이터베이스의 user name 가져오기
        """
        return self.user_name
    
    def close(self):
        """DB 닫기
        """
        self.cursor.close()
        self.connection.close()

            
    def __init__(self):
        """아무 인자없이 클래스 최초 생성
        """
        super.__init__()

    def __init__(self, env_name:str):
        """str입력시 해당 변수명으로 접속하는 클래스 최초 생성
        """
        self.make_connection(env_name)


def main():
    print("테스트")
