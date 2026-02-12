#!/usr/bin/env python3
"""
포스텔러 테스트 결과 DB 뷰어
Flask 앱으로 테스트 결과 검색 및 조회

실행:
    .venv/bin/python viewer.py
    또는
    source .venv/bin/activate && python viewer.py

접속:
    http://localhost:5000
"""

from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path

app = Flask(__name__)

DB_PATH = Path(__file__).parent / "data" / "forceteller_test.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_records():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, test_no, input_date, input_time, gender, location,
               ft_year_pillar, ft_month_pillar, ft_day_pillar, ft_hour_pillar,
               pillar_match, element_diff_max, strength_match, created_at
        FROM test_results
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_record_by_id(record_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_results WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def delete_record(record_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM test_results WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def delete_all_records():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM test_results")
    conn.commit()
    conn.close()


def search_records(input_date: str = "", input_time: str = "", 
                   gender: str = "", location: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM test_results WHERE 1=1"
    params = []
    
    if input_date:
        query += " AND input_date = ?"
        params.append(input_date)
    if input_time:
        query += " AND input_time = ?"
        params.append(input_time)
    if gender:
        query += " AND gender = ?"
        params.append(gender)
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    
    query += " ORDER BY id DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


@app.route("/")
def index():
    input_date = request.args.get("date", "").strip()
    input_time = request.args.get("time", "").strip()
    gender = request.args.get("gender", "").strip()
    location = request.args.get("location", "").strip()
    
    if any([input_date, input_time, gender, location]):
        records = search_records(input_date, input_time, gender, location)
        search_performed = True
    else:
        records = get_all_records()
        search_performed = False
    
    return render_template("viewer.html", 
                         records=records,
                         search_performed=search_performed,
                         search_date=input_date,
                         search_time=input_time,
                         search_gender=gender,
                         search_location=location)


@app.route("/detail/<int:record_id>")
def detail(record_id: int):
    record = get_record_by_id(record_id)
    if not record:
        return "레코드를 찾을 수 없습니다.", 404
    
    return render_template("detail.html", record=record)


@app.route("/delete/<int:record_id>", methods=["POST"])
def delete(record_id: int):
    delete_record(record_id)
    return redirect(url_for('index'))


@app.route("/delete/all", methods=["POST"])
def delete_all():
    delete_all_records()
    return redirect(url_for('index'))


if __name__ == "__main__":
    print(f"DB 경로: {DB_PATH}")
    print("서버 시작: http://localhost:8000")
    app.run(debug=True, host="0.0.0.0", port=8000)
