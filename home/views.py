# home > views.py
from django.shortcuts import render

def home_page(request):
    return render(request, "home/home.html")

def home(request):
    # 실제 DB에서 보호대상자 정보를 불러오는 자리 (지금은 하드코딩)
    users = [
        {"name": "박주연", "gender": "여성", "age": 23, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "활동중"},
        {"name": "박해름", "gender": "여성", "age": 24, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "활동중"},
        {"name": "김승연", "gender": "여성", "age": 22, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "비활동중"},
        {"name": "김지민", "gender": "여성", "age": 24, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "활동중"},
        {"name": "김하정", "gender": "여성", "age": 25, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "비활동중"},
        {"name": "문정윤", "gender": "여성", "age": 21, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "비활동중"},
        {"name": "신윤지", "gender": "여성", "age": 20, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "비활동중"},
        {"name": "안희랑", "gender": "여성", "age": 23, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "비활동중"},
        {"name": "오긍요", "gender": "여성", "age": 22, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "비활동중"},
        {"name": "홍지연", "gender": "여성", "age": 21, "address": "서울특별시 성북구 보문로34다길 2", "phone": "010-1234-5678", "status": "비활동중"},
    ]
    return render(request, "home/home.html", {"users": users})
