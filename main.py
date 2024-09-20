import sys
import os

import logging
import datetime
import click

from typing import Annotated, List, TypedDict
import operator

import sqlalchemy
from connect_connector import connect_with_connector
from connect_connector_auto_iam_authn import connect_with_connector_auto_iam_authn

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import VertexAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

logger = logging.getLogger()

db = None

GOOGLE_AI=os.environ.get("GOOGLE_AI")

# LLM初期化
if GOOGLE_AI == "GEMINI":
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
else:
    llm = VertexAI(model="gemini-1.5-flash")
    #llm = VertexAI(model="gemini-1.0-pro")

def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    return (
        connect_with_connector_auto_iam_authn()
        if os.environ.get("DB_IAM_USER")
        else connect_with_connector()
    )

    raise ValueError(
        "Missing database connection type. Please define one of INSTANCE_CONNECTION_NAME"
    )

def main():
  
    global db
    if db is None:
        db = init_connection_pool()

    stmt = sqlalchemy.text('SELECT * FROM questionnaire where start_date is null order by questionnaire_id')
    try:
        with db.connect() as conn:
            res = conn.execute(stmt)
            questionnaires = res.fetchall()
    except Exception as e:
        logger.exception(e)

    # 未実施のアンケート一覧を取得して、繰り返す。
    for questionnaire in questionnaires:

        # アンケート回答の初期化
        answer = ""
        result = ""

        # AI Questionnaire Start
        start_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = """
        UPDATE questionnaire
           SET start_date = :start_date,
               questionnaire_status = :questionnaire_status,
               updated_date = :updated_date
         WHERE questionnaire_id = :questionnaire_id
        """
        stmt = sqlalchemy.text(query)
        try:
            with db.connect() as conn:
                conn.execute(
                    stmt, parameters={
                        "questionnaire_id": questionnaire.questionnaire_id, "start_date": start_date,
                        "questionnaire_status": 2, "updated_date": start_date
                    }
                )
                conn.commit()
        except Exception as e:
            logger.exception(e)

        # アンケート回答者の一覧を取得する。
        query2 = """
            SELECT p.*, s.sex_name, st.stereo_content
              FROM personality as p
              JOIN sex as s on p.sex = s.sex
              JOIN stereo_type as st on p.stereo_type = st.stereo_type
             WHERE p.deleted_date is null 
        """
        # 性別の条件
        if questionnaire.sex_range == 2: # 1の時は全員なので、追加なし
            query2 = query2 + " AND p.sex in (1,2) "
        elif questionnaire.sex_range == 3:
            query2 = query2 + " AND p.sex = 1 "
        elif questionnaire.sex_range == 4:
            query2 = query2 + " AND p.sex = 2 "

        # 年齢の条件
        if questionnaire.age_range == 1: # 0の時は全員なので、追加なし
            query2 = query2 + " AND p.age < 20 "
        elif questionnaire.age_range == 2:
            query2 = query2 + " AND p.age >= 20 AND p.age < 30 "
        elif questionnaire.age_range == 3:
            query2 = query2 + " AND p.age >= 30 AND p.age < 40 "
        elif questionnaire.age_range == 4:
            query2 = query2 + " AND p.age >= 40 AND p.age < 60 "
        elif questionnaire.sex_range == 5:
            query2 = query2 + " AND p.sex >= 60 "

        stmt2 = sqlalchemy.text(query2)
        try:
            with db.connect() as conn:
                res = conn.execute(stmt2)
                personalities = res.fetchall()
        except Exception as e:
            logger.exception(e) 

        for personality in personalities:
            # ここで生成AIでアンケート回答を生成する。
            sys_msg = "あなたは次に示すような人物です。" + personality.stereo_content + "あなたはこの人物になりきって、100文字以内で回答してみてください。"

            # llm = VertexAI(model="gemini-1.5-flash")
            resp = llm.invoke(sys_msg + questionnaire.question)
            print(str(resp))
            
            if GOOGLE_AI == "GEMINI": # Geminiの場合はresp.content  VertexAIの場合はresp
                resp = resp.content

            answer = answer + "■" + personality.name + "," + personality.sex_name + "," + str(personality.age) + "歳," + resp + "\n"

        # まとめ
        result = llm.invoke("あなたは優秀なアンケート集計者です。次のアンケート回答を200文字程度で集計して、まとめてください。\n\nアンケート回答:" + answer)

        if GOOGLE_AI == "GEMINI": # Geminiの場合はresult.content  VertexAIの場合はresult
            result = result.content
            
        end_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query3 = """
            UPDATE questionnaire
               SET result = :result,
                   answer_cnt = :answer_cnt,
                   answer = :answer,
                   end_date = :end_date,
                   questionnaire_status = :questionnaire_status,
                   updated_date = :updated_date
             WHERE questionnaire_id = :questionnaire_id
        """
        stmt3 = sqlalchemy.text(query3)
        try:
            with db.connect() as conn:
                conn.execute(
                    stmt3, parameters={
                        "questionnaire_id": questionnaire.questionnaire_id, "result": result, "answer_cnt": len(personalities),
                        "answer": answer, "end_date": end_date, "questionnaire_status": 3, "updated_date": end_date
                    }
                )
                conn.commit()
        except Exception as e:
            logger.exception(e)            

if __name__ == "__main__":
    main()

