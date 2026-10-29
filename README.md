# 리뷰 분석 리포트 템플릿

리뷰 데이터로 11쪽 분석 리포트 PDF 를 만드는 템플릿입니다. 디자인은 코드에 고정돼 있고, 내용은 report_data.json 하나만 바꾸면 됩니다.

- build_report.py : 레이아웃과 렌더
- report_style.css : 디자인
- report_data.json : 예시 데이터(토니모리 세라마이드 모찌 토너). 새 제품은 이 키 구조 그대로 값만 바꿉니다
- nousgirl_b64.txt : 표지 그림

실행: python build_report.py 새데이터.json 리포트.pdf
필요한 것: 파이썬, playwright, pymupdf, pillow, 설치된 크롬

Architected by 장성윤 · the-underdogs.kr
